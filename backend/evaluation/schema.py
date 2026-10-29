"""Independent annotation contract. Predictions cannot promote annotations."""
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, get_args
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator, field_validator

CATEGORIES = {'national_health_insurance','residence_tax','national_pension','utility',
              'school','employment','municipal','unknown'}
ISSUED_PROVENANCES = {'real_private','anonymized_real'}
PROVENANCES = ('real_private','anonymized_real','public_sample_form','synthetic')


def dataset_group(provenance):
    if provenance in ISSUED_PROVENANCES:return 'issued_documents'
    if provenance=='public_sample_form':return 'public_sample_forms'
    if provenance=='synthetic':return 'synthetic_fixtures'
    raise ValueError('Unsupported dataset provenance.')
DEADLINE_KINDS = Literal['payment','submission','application','acceptance','response','return','usage_expiration','validity_expiration']
AMOUNT_KINDS = Literal['payment','billed','total','outstanding','late_fee','paid','tax','unknown']
Page = Annotated[StrictInt, Field(ge=1,le=5)]
Money = Annotated[StrictInt, Field(ge=0)]


class Annotation(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True)


class Evidence(Annotation):
    text: str = Field(min_length=1,max_length=4000)
    page: Page


class Deadline(Annotation):
    kind: DEADLINE_KINDS
    date: str
    label: str = Field(min_length=1,max_length=100)
    evidence: list[Evidence] = Field(min_length=1,max_length=20)

    @field_validator('date')
    @classmethod
    def iso_date(cls,value):
        if date.fromisoformat(value).isoformat()!=value:raise ValueError('Use an exact ISO date.')
        return value


class Amount(Annotation):
    kind: AMOUNT_KINDS
    value: Money
    label: str = Field(min_length=1,max_length=100)
    evidence: list[Evidence] = Field(min_length=1,max_length=20)


class UncertainField(Annotation):
    field: Literal['deadlines','amounts']
    kind: str
    date: str | None = None
    value: Money | None = None
    evidence: list[Evidence] = Field(min_length=1,max_length=20)
    reason: Literal['source_ambiguous','source_unreadable','conditional','illustrative','low_confidence_input','invalid_literal','competing_values']
    mustNotBePrimary: bool = True

    @model_validator(mode='after')
    def compatible_role(self):
        if self.kind not in get_args(DEADLINE_KINDS if self.field=='deadlines' else AMOUNT_KINDS):raise ValueError('Use a role appropriate to this field.')
        if self.field=='deadlines' and self.value is not None or self.field=='amounts' and self.date is not None:raise ValueError('Date and money values cannot be mixed.')
        if self.date is not None and date.fromisoformat(self.date).isoformat()!=self.date:raise ValueError('Use an exact ISO candidate date or null.')
        return self


class EraCheck(Annotation):
    literal: str = Field(min_length=1,max_length=50)
    expectedDate: str | None
    kind: DEADLINE_KINDS
    page: Page

    @field_validator('expectedDate')
    @classmethod
    def iso_date(cls,value):
        if value is not None and date.fromisoformat(value).isoformat()!=value:raise ValueError('Use an exact ISO date or null.')
        return value


class RepeatedAmount(Annotation):
    kind: AMOUNT_KINDS
    value: Money
    occurrences: Annotated[StrictInt, Field(ge=2,le=100)]


class Verification(Annotation):
    status: Literal['unreviewed','partial','verified']
    method: Literal['pending','independent_human','synthetic_specification']
    reviewerId: str | None = Field(default=None,pattern=r'^H\d{3}$')


class PilotReview(Annotation):
    reviewerId: str = Field(pattern=r'^H\d{3}$')
    independentOfPrediction: bool
    categoryReviewed: bool
    deadlinesAndMeaningsReviewed: bool
    amountsAndLabelsReviewed: bool
    paidAndUnpaidReviewed: bool
    multipleDatesAndAmountsReviewed: bool
    missingAndAmbiguousReviewed: bool
    japaneseEvidenceReviewed: bool
    englishInterpretationReviewed: bool


class GroundTruth(Annotation):
    verification: Verification
    complete: bool = False
    documentType: str | None = Field(default=None,min_length=1,max_length=200)
    deadlines: list[Deadline] = Field(default_factory=list,max_length=100)
    amounts: list[Amount] = Field(default_factory=list,max_length=100)
    primaryDeadline: str | None = None
    primaryAmount: Money | None = None
    extractionStatus: Literal['verified','partial','unverified','no_fields'] | None = None
    missingFields: list[Literal['deadlines','amounts','documentType','primaryDeadline','primaryAmount']] = Field(default_factory=list)
    uncertainFields: list[UncertainField] = Field(default_factory=list,max_length=100)
    eraChecks: list[EraCheck] = Field(default_factory=list,max_length=100)
    repeatedAmounts: list[RepeatedAmount] = Field(default_factory=list,max_length=100)
    transcription: str | None = Field(default=None,max_length=10000)
    englishInterpretation: str | None = Field(default=None,min_length=1,max_length=2000)
    pilotReview: PilotReview | None = None

    @field_validator('englishInterpretation')
    @classmethod
    def english_prose(cls,value):
        import re
        if value is not None and re.search(r'[\u3040-\u30ff\u3400-\u9fff]',value):raise ValueError('Write English interpretation separately from original Japanese source evidence.')
        return value

    @model_validator(mode='after')
    def independent_review(self):
        verification=self.verification
        if self.complete!=(verification.status=='verified'):raise ValueError('Complete truth requires explicit verified annotation.')
        if self.complete and not {'deadlines','amounts'}<=self.model_fields_set:raise ValueError('Explicitly enumerate both field lists, including genuine empty lists.')
        if verification.status=='unreviewed':
            if verification.method!='pending' or self.deadlines or self.amounts or self.uncertainFields or self.eraChecks or self.repeatedAmounts or self.missingFields or self.model_fields_set-{'verification','complete'}:
                raise ValueError('Unreviewed truth must not assert facts, nulls or absence.')
        elif verification.method=='pending':raise ValueError('Reviewed truth requires an independent method.')
        if verification.method=='independent_human' and not verification.reviewerId:raise ValueError('Use an anonymous reviewer ID.')
        for name in self.missingFields:
            value=getattr(self,name)
            if (value!=[] if name in {'deadlines','amounts'} else value is not None):raise ValueError('Missing-field assertions cannot conflict with annotated values, including zero.')
        if len(self.missingFields)!=len(set(self.missingFields)) or any(u.field in self.missingFields for u in self.uncertainFields):raise ValueError('Missing and uncertain fields must be consistent and distinct.')
        if self.primaryDeadline and self.primaryDeadline not in {d.date for d in self.deadlines if d.kind not in {'usage_expiration','validity_expiration'}}:raise ValueError('A primary deadline must be an explicit annotated action deadline.')
        if self.primaryAmount is not None and self.primaryAmount not in {a.value for a in self.amounts if a.kind in {'payment','billed','total','outstanding'}}:raise ValueError('A primary amount must have an eligible annotated role.')
        return self


class Document(Annotation):
    id: str = Field(pattern=r'^[RSP]\d{3}$')
    path: str
    inputSha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    provenance: Literal['synthetic','real_private','anonymized_real','public_sample_form']
    category: str | None
    authorizationConfirmed: bool
    variant: str = Field(default='unspecified',pattern=r'^[a-z0-9_]{1,60}$')
    groundTruth: GroundTruth

    @model_validator(mode='after')
    def provenance_and_review(self):
        if self.category is not None and self.category not in CATEGORIES:raise ValueError('Unsupported category.')
        prefix='S' if self.provenance=='synthetic' else 'P' if self.provenance=='public_sample_form' else 'R'
        if not self.id.startswith(prefix):raise ValueError('Sample IDs must distinguish issued documents, public forms and synthetic inputs.')
        if self.provenance!='synthetic' and self.groundTruth.verification.method=='synthetic_specification':raise ValueError('Synthetic specifications are not human ground truth for issued documents or public forms.')
        if self.provenance=='synthetic' and self.groundTruth.verification.method=='independent_human':raise ValueError('Keep generated specifications separate from real review.')
        if self.groundTruth.verification.status!='unreviewed' and self.category is None:raise ValueError('Reviewed samples require an explicit category, including unknown.')
        return self


class Dataset(Annotation):
    schemaVersion: Literal[2] = 2
    targetRealDocuments: Literal[40] = 40
    documents: list[Document] = Field(min_length=1,max_length=50)

    @model_validator(mode='after')
    def distinct_documents(self):
        if len({d.id for d in self.documents})!=len(self.documents) or len({str(Path(d.path).expanduser().resolve()) for d in self.documents})!=len(self.documents) or len({d.inputSha256 for d in self.documents})!=len(self.documents):
            raise ValueError('Use distinct IDs and input files; record variants separately when appropriate.')
        return self


def truth_dict(document):
    """Keep omitted optional facts unscored: null is an explicit assertion."""
    truth=document.groundTruth.model_dump(exclude_unset=True)
    truth.setdefault('deadlines',[]);truth.setdefault('amounts',[])
    truth.setdefault('complete',False)
    return truth


def load_dataset(path):
    path=Path(path).expanduser().resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError('Keep sensitive datasets outside the checkout.')
    if path.stat().st_size>8*1024**2:raise ValueError('Annotation file exceeds the bounded limit.')
    return Dataset.model_validate_json(path.read_bytes())
