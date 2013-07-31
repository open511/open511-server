from collections import namedtuple
import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from dateutil import rrule
import pytz

from open511.utils.cache import memoize_method

Period = namedtuple('Period', 'start end')


def text_to_date(s):
    return datetime.date(*[int(x) for x in s.split('-')]) if s else None

def text_to_time(s):
    return datetime.time(*[int(x) for x in s.split(':')]) if s else None

def _time_el_to_period(t):
    return Period(
        text_to_time(t.findtext('start')),
        text_to_time(t.findtext('end'))
    )

def _time_text_to_period(t):
    (start, _, end) = t.partition('-')
    return Period(
        text_to_time(start),
        text_to_time(end)
    )

# FIXME write tests!

class Schedule(object):

    def __init__(self, root, default_timezone=None):
        assert root.tag == 'schedule'
        self.root = root
        self.default_timezone = default_timezone

    @property
    @memoize_method
    def specific_dates(self):
        """A dict of dates -> Period time tuples representing exceptions
        to the base recurrence pattern."""
        ex = {}
        for sd in self.root.xpath('specific_dates/specific_date'):
            bits = sd.split(' ')
            date = text_to_date(bits.pop(0))
            ex.setdefault(date, []).extend([
                _time_text_to_period(t)
                for t in bits
            ])
        return ex

    @property
    @memoize_method
    def timezone(self):
        tzname = self.root.findtext('timezone')
        if tzname:
            return pytz.timezone(tzname)
        elif self.default_timezone:
            return self.default_timezone
        else:
            raise ValidationError("The event doesn't have a timezone, and nor does the jurisdiction.")

    def to_timezone(self, dt):
        """Converts a datetime to the timezone of this Schedule."""
        if timezone.is_aware(dt):
            return dt.astimezone(self.timezone)
        else:
            return timezone.make_aware(dt, self.timezone)

    def includes(self, query):
        """Does this schedule include the provided time?
        query should be a datetime (naive or timezone-aware)"""
        query = self.to_timezone(query)
        query_date = query.date()
        query_time = query.time()

        # Is the provided time an exception for this schedule?
        specific = self.specific_dates.get(query_date)
        if specific is not None:
            if not query_time:
                return True
            for period in specific:
                if query_time >= period.start and query_time <= period.end:
                    return True

        # It's not an exception. Is it within the standard range?

        if self.start_date and query_date < self.start_date:
            return False
        if self.end_date and query_date > self.end_date:
            return False
        if query_date.weekday() not in self.weekdays:
            return False

        if not query_time:
            return True

        for period in self.default_times:
            if query_time >= period.start and query_time <= period.end:
                return True

        return False

    def active_within_range(self, query_start, query_end):
        """Is this event ever active between query_start and query_end,
        which are (aware or naive) datetimes?"""

        query_start = self.to_timezone(query_start)
        query_end = self.to_timezone(query_end)

        for range in self.to_periods(range_start=query_start.date(), range_end=query_end.date()):
            if (
                    ((range.start < query_start) and (range.end > query_end))
                    or (query_start <= range.start <= query_end)
                    or (query_start <= range.end <= query_end)):
                return True
        return False

    def has_remaining_periods(self):
        now = timezone.now().astimezone(self.timezone)
        periods = self.to_periods(range_start=now.date(), infinite_limit=2)
        return any(p for p in periods if p.end > now)

    def to_periods(self, infinite_limit=None,
            range_start=datetime.date.min, range_end=datetime.date.max):
        """A list of datetime tuples representing all the periods for which
        this event is active.

        If the event has no end_date, you must provide an infinite_limit argument.

        range_start and range_end are datetime.date objects limiting the periods returned
        """

        tz = self.timezone
        def _combine(base, periods):
            return [
                Period(
                    tz.localize(datetime.datetime.combine(base, period.start)),
                    tz.localize(datetime.datetime.combine(base, period.end))
                ) for period in periods
            ]

        base = []
        if self.start_date:
            kw = {
                'dtstart': max(range_start, self.start_date),
                'freq': rrule.DAILY,
                'byweekday': list(self.weekdays),
            }
            if self.end_date:
                kw['until'] = min(range_end, self.end_date)
            else:
                if range_end < datetime.date.max:
                    kw['until'] = range_end
                elif infinite_limit:
                    kw['count'] = infinite_limit
                else:
                    raise ValueError("Neither an end date nor a limit was provided.")
            base = list(rrule.rrule(**kw))

        # Copy, since we'll be deleting keys
        exceptions = dict(self.specific_dates)
        periods = []
        for base_date in base:
            if base_date in exceptions:
                periods.extend(_combine(base_date, exceptions[base_date]))
                del exceptions[base_date]
            else:
                periods.extend(_combine(base_date, self.default_times))

        if exceptions:
            for date, periods in exceptions.values():
                if date >= range_start and date <= range_end:
                    periods.extend(_combine(date, periods))
            periods.sort(key=lambda p: p[0])

        return periods

    @property
    def start_date(self):
        """Start date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('start_date'))

    @property
    def end_date(self):
        """End date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('end_date'))

    @property
    @memoize_method
    def default_times(self):
        """The standard daily times (e.g. 9:00-11:00, 15:00-17:00) for the recurring
        event, as an array of Period tuples."""
        dt = [
            _time_el_to_period(t)
            for t in self.root.xpath('times/time')
        ]
        if not dt:
            dt = [
                Period(datetime.time(0, 0), datetime.time(23, 59))
            ]
        return dt

    @property
    def weekdays(self):
        """A set of integers representing the weekdays the event recurs on,
        with Monday = 0 and Sunday = 6."""
        if not self.root.xpath('days'):
            return set(range(7))
        return set(int(d) - 1 for d in self.root.xpath('days/day/text()'))
