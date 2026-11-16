"""Core API routes: report downloads."""
from django.urls import path

from .views import bracket_report, results_report, weighing_report

urlpatterns = [
    path("reports/weighing.xlsx", weighing_report, name="report-weighing"),
    path("reports/bracket/<int:bracket_id>.xlsx", bracket_report, name="report-bracket"),
    path("reports/results.docx", results_report, name="report-results"),
]

