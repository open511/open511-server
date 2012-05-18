from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from open511.utils import serialization

class RoadEvent(models.Model):
    
    EVENT_TYPES = [
        ('RW', _('Road work')),
        ('AC', _('Accident')),
        ('WE', _('Weather')),
        ('EV', _('Scheduled event (non-construction)')),
    ]
    
    SEVERITY_CHOICES = [
        ('1', _('Minor')),
        ('2', _('Major')),
        ('3', _('Apocalyptic')),
    ]
    
    source_id = models.CharField(max_length=100, blank=True, help_text=_('A unique ID for this event. Will be assigned automatically if left blank.'))
    jurisdiction = models.CharField(max_length=100, help_text=_('e.g. ville.montreal.qc.ca')) 
    title = models.CharField(blank=True, max_length=500)
    
    geom = models.GeometryField(verbose_name=_('Geometry'))

    affected_roads = models.TextField(blank=True) # human-readable
    description = models.TextField(blank=True)
    type = models.CharField(max_length=2, choices=EVENT_TYPES, default='RW')
    severity = models.CharField(blank=True, max_length=2, choices=SEVERITY_CHOICES)
    closed = models.NullBooleanField(blank=True, help_text=_('Is the road entirely closed? Choose No if the road remains partially open.'))
    traffic_restrictions = models.TextField(blank=True, help_text=_('e.g. temporary speed limits, size/weight limits'))
    detour = models.TextField(blank=True, help_text=_('Description of alternate route(s)'))
    external_url = models.URLField(blank=True, help_text=_('If available, URL to a full record for this event on an external site.'))

    # Dates and times will need to modeled in a much more complex way eventually,
    # but this'll do for now.
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    def __unicode__(self):
        return self.title if self.title else self.source_id
    
    def save(self, *args, **kwargs):
        super(RoadEvent, self).save(*args, **kwargs)
        if not self.source_id:
            self.source_id = self.id
            self.save()

    def to_xml_element(self):
        return serialization.roadevent_to_xml_element(self)

    def to_json_structure(self):
        return serialization.roadevent_to_json_structure(self)
