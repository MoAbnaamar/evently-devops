from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models import Form, FormCreate, Submission, SubmissionCreate


# Custom exception raised when a requested form is not found
class FormNotFoundError(Exception):
    pass


# Process-local storage for forms and submissions
class InMemoryStore:
    # Initialize internal storage dictionaries
    def __init__(self) -> None:
        self._forms: dict[UUID, Form] = {}
        self._submissions: dict[UUID, list[Submission]] = {}

    # Create and store a new form
    def create_form(self, payload: FormCreate) -> Form:
        form = Form(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self._forms[form.id] = form
        self._submissions[form.id] = []
        return form

    # Retrieve a form by ID or raise FormNotFoundError
    def get_form(self, form_id: UUID) -> Form:
        form = self._forms.get(form_id)
        if form is None:
            raise FormNotFoundError(str(form_id))
        return form

    # Create and save a new submission for a specific form
    def add_submission(self, form_id: UUID, payload: SubmissionCreate) -> Submission:
        self.get_form(form_id)  # Verify form exists before adding submission
        submission = Submission(
            id=uuid4(),
            form_id=form_id,
            data=payload.data,
            submitted_at=datetime.now(UTC),
        )
        self._submissions[form_id].append(submission)
        return submission

    # Retrieve all submissions for a specific form ID
    def list_submissions(self, form_id: UUID) -> list[Submission]:
        self.get_form(form_id) # Verify form exists before listing submissions
        return list(self._submissions[form_id])