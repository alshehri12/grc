"""
Frameworks models for the GRC system.
ISO 27001, NCA ECC, SAMA CSF, PDPL libraries.
This app handles pre-loaded framework data.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


# Note: The main framework models are in the compliance app.
# This app is primarily for data fixtures and framework-specific utilities.


class FrameworkTemplate(models.Model):
    """
    قالب الإطار - Framework template for importing standard controls
    """
    code = models.CharField(_('Framework Code'), max_length=50, unique=True)
    name = models.CharField(_('Framework Name'), max_length=200)
    name_ar = models.CharField(_('اسم الإطار'), max_length=200, blank=True)
    version = models.CharField(_('Version'), max_length=20)
    
    description = models.TextField(_('Description'), blank=True)
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    # Template data (JSON structure with domains and controls)
    template_data = models.JSONField(_('Template Data'), default=dict)
    
    # Mapping data for cross-framework references
    mapping_data = models.JSONField(_('Mapping Data'), default=dict, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Framework Template')
        verbose_name_plural = _('Framework Templates')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.version})"


class ControlMapping(models.Model):
    """
    ربط الضوابط - Cross-framework control mapping
    """
    source_framework = models.CharField(_('Source Framework'), max_length=50)
    source_control_id = models.CharField(_('Source Control ID'), max_length=50)
    
    target_framework = models.CharField(_('Target Framework'), max_length=50)
    target_control_id = models.CharField(_('Target Control ID'), max_length=50)
    
    # Mapping strength
    MAPPING_TYPES = [
        ('full', _('Full Mapping')),
        ('partial', _('Partial Mapping')),
        ('related', _('Related')),
    ]
    mapping_type = models.CharField(_('Mapping Type'), max_length=20, choices=MAPPING_TYPES, default='full')
    
    notes = models.TextField(_('Notes'), blank=True)
    notes_ar = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        verbose_name = _('Control Mapping')
        verbose_name_plural = _('Control Mappings')
        unique_together = ['source_framework', 'source_control_id', 'target_framework', 'target_control_id']
    
    def __str__(self):
        return f"{self.source_framework}:{self.source_control_id} -> {self.target_framework}:{self.target_control_id}"


class RegulatoryRequirement(models.Model):
    """
    المتطلب التنظيمي - Regulatory requirement reference
    """
    REQUIREMENT_TYPES = [
        ('mandatory', _('Mandatory')),
        ('recommended', _('Recommended')),
        ('optional', _('Optional')),
    ]
    
    framework_code = models.CharField(_('Framework Code'), max_length=50)
    requirement_id = models.CharField(_('Requirement ID'), max_length=50)
    
    title = models.CharField(_('Title'), max_length=500)
    title_ar = models.CharField(_('العنوان'), max_length=500, blank=True)
    
    description = models.TextField(_('Description'))
    description_ar = models.TextField(_('الوصف'), blank=True)
    
    requirement_type = models.CharField(_('Requirement Type'), max_length=20, choices=REQUIREMENT_TYPES, default='mandatory')
    
    # For PDPL: article references
    article_reference = models.CharField(_('Article Reference'), max_length=100, blank=True)
    
    # Related controls
    related_control_ids = models.JSONField(_('Related Control IDs'), default=list)
    
    # Penalties for non-compliance (if applicable)
    penalty_description = models.TextField(_('Penalty Description'), blank=True)
    penalty_description_ar = models.TextField(_('وصف العقوبة'), blank=True)
    
    class Meta:
        verbose_name = _('Regulatory Requirement')
        verbose_name_plural = _('Regulatory Requirements')
        unique_together = ['framework_code', 'requirement_id']
    
    def __str__(self):
        return f"{self.framework_code} - {self.requirement_id}: {self.title[:50]}"
