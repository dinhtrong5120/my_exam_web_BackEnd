from io import BytesIO
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from openpyxl import Workbook
from .models import Exam, Attempt


class ExamFlowTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='teacher', password='password123')
        self.other = get_user_model().objects.create_user(username='student', password='password123')
        self.client.force_authenticate(self.owner)

    def test_create_edit_publish_take_and_keep_answers_private(self):
        response = self.client.post('/api/exams/', {'title': 'Mini TOEIC', 'duration_minutes': 10})
        self.assertEqual(response.status_code, 201)
        exam_id = response.data['id']
        question = {'part': 'Part 5', 'prompt': 'Choose the answer.', 'points': 2,
                    'explanation': 'B is correct.', 'choices': [
                        {'text': 'A', 'is_correct': False}, {'text': 'B', 'is_correct': True}]}
        response = self.client.patch(f'/api/exams/{exam_id}/', {'questions': [question]}, format='json')
        self.assertEqual(response.status_code, 200)
        qid = response.data['questions'][0]['id']
        correct_id = response.data['questions'][0]['choices'][1]['id']
        self.assertEqual(self.client.post(f'/api/exams/{exam_id}/publish/', {}).status_code, 200)
        self.client.force_authenticate(self.other)
        response = self.client.get(f'/api/exams/{exam_id}/')
        self.assertNotIn('is_correct', response.data['questions'][0]['choices'][0])
        self.assertNotIn('explanation', response.data['questions'][0])
        self.assertEqual(self.client.patch(f'/api/exams/{exam_id}/', {'title': 'Stolen'}).status_code, 403)
        self.client.force_authenticate(user=None)
        response = self.client.post(f'/api/exams/{exam_id}/submit/',
            {'answers': {str(qid): correct_id}, 'guest_name': 'Learner'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['score'], 2)
        self.assertEqual(Attempt.objects.count(), 1)

    def test_invalid_question_does_not_replace_existing(self):
        exam = Exam.objects.create(owner=self.owner, title='Draft')
        good = {'prompt': 'Question', 'choices': [
            {'text': 'Yes', 'is_correct': True}, {'text': 'No', 'is_correct': False}]}
        self.client.patch(f'/api/exams/{exam.id}/', {'questions': [good]}, format='json')
        bad = {'prompt': 'Bad', 'choices': [
            {'text': 'One', 'is_correct': True}, {'text': 'Two', 'is_correct': True}]}
        response = self.client.patch(f'/api/exams/{exam.id}/', {'questions': [bad]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(exam.questions.get().prompt, 'Question')

    def test_import_template_columns(self):
        exam = Exam.objects.create(owner=self.owner, title='Import')
        book = Workbook()
        sheet = book.active
        sheet.append(['Nội dung câu hỏi', 'Giải thích', 'Điểm', 'Phương án 1', 'Đúng/Sai 1', 'Phương án 2', 'Đúng/Sai 2'])
        sheet.append(['Choose.', 'Explanation', 1, 'Yes', 'true', 'No', 'false'])
        out = BytesIO()
        book.save(out)
        out.seek(0)
        file = SimpleUploadedFile('questions.xlsx', out.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response = self.client.post(f'/api/exams/{exam.id}/import/', {'file': file}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported'], 1)
        self.assertEqual(exam.questions.count(), 1)

    def test_import_supplied_workbook_and_grade_multiple_answers(self):
        exam = Exam.objects.create(owner=self.owner, title='Imported workbook', is_published=True)
        source = Path(__file__).resolve().parents[2] / 'exam_questions.xlsx'
        file = SimpleUploadedFile('exam_questions.xlsx', source.read_bytes(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response = self.client.post(f'/api/exams/{exam.id}/import/', {'file': file}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['imported'], 51)
        multiple = exam.questions.filter(question_type='multiple')
        self.assertEqual(multiple.count(), 12)
        question = multiple.first()
        correct_ids = list(question.choices.filter(is_correct=True).values_list('id', flat=True))
        self.assertGreaterEqual(len(correct_ids), 2)
        self.client.force_authenticate(user=None)
        url = f'/api/exams/{exam.id}/submit/'
        partial = self.client.post(url, {'answers': {str(question.id): correct_ids[:1]}}, format='json')
        self.assertEqual(partial.status_code, 201)
        self.assertEqual(partial.data['score'], 0)
        complete = self.client.post(url, {'answers': {str(question.id): correct_ids}}, format='json')
        self.assertEqual(complete.status_code, 201)
        self.assertEqual(complete.data['score'], question.points)
        self.assertEqual(complete.data['details'][question.position - 1]['correct_choice_ids'], correct_ids)

    def test_personal_history_keeps_review_after_exam_changes_and_deletion(self):
        exam = Exam.objects.create(owner=self.owner, title='Original title',
            description='Original description', is_published=True)
        response = self.client.patch(f'/api/exams/{exam.id}/', {'questions': [{
            'prompt': 'Original question', 'choices': [
                {'text': 'Right', 'is_correct': True}, {'text': 'Wrong', 'is_correct': False}]
        }]}, format='json')
        question = response.data['questions'][0]
        self.client.force_authenticate(self.other)
        submitted = self.client.post(f'/api/exams/{exam.id}/submit/', {
            'answers': {str(question['id']): question['choices'][0]['id']}
        }, format='json')
        self.assertEqual(submitted.status_code, 201)
        attempt_id = submitted.data['id']
        self.assertEqual(len(self.client.get('/api/attempts/').data), 1)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/attempts/').data, [])
        self.assertEqual(self.client.get(f'/api/attempts/{attempt_id}/').status_code, 404)
        changed = self.client.patch(f'/api/exams/{exam.id}/', {
            'title': 'Changed title', 'description': 'Changed description', 'questions': [{
                'prompt': 'Changed question', 'choices': [
                    {'text': 'New answer', 'is_correct': False},
                    {'text': 'Different answer', 'is_correct': True}]
            }]
        }, format='json')
        self.assertEqual(changed.status_code, 200)
        self.client.force_authenticate(self.other)
        updated = self.client.get('/api/attempts/').data[0]
        self.assertEqual(updated['exam_title'], 'Changed title')
        self.assertEqual(updated['exam_description'], 'Changed description')
        self.assertEqual(self.client.get(f'/api/attempts/{attempt_id}/').data['questions'][0]['prompt'], 'Original question')
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(f'/api/exams/{exam.id}/').status_code, 204)
        self.client.force_authenticate(self.other)
        detail = self.client.get(f'/api/attempts/{attempt_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['exam_title'], 'Changed title')
        self.assertEqual(detail.data['exam_description'], 'Changed description')
        self.assertIsNone(detail.data['exam_id'])
        self.assertEqual(detail.data['questions'][0]['prompt'], 'Original question')
        self.assertEqual(detail.data['questions'][0]['choices'][0]['text'], 'Right')
        self.assertEqual(detail.data['score'], 1)

    def test_guest_attempt_is_not_added_to_account_history(self):
        exam = Exam.objects.create(owner=self.owner, title='Guest exam', is_published=True)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(f'/api/exams/{exam.id}/submit/', {
            'answers': {}
        }, format='json').status_code, 201)
        self.assertEqual(self.client.get('/api/attempts/').status_code, 401)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/attempts/').data, [])
