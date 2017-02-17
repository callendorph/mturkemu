from django.contrib import admin

from .models import *

models = [
    Worker,
    Requester,
    Credential,
    Qualification,
    Locale,
    QualificationRequest,
    QualificationGrant,
    QualificationRequirement,
    TaskType,
    Task,
    Assignment,
    BonusPayment,
    WorkerBlock
    ]

for model in models:
    admin.site.register(model)
