from collections import namedtuple
import datetime
from operator import itemgetter

from django.core.exceptions import ValidationError
from django.utils import timezone

from dateutil import rrule
import pytz

from open511_server.utils.cache import memoize_method

Period = namedtuple('Period', 'start end')


def text_to_date(s):
    return datetime.date(*[int(x) for x in s.split('-')]) if s else None

def text_to_time(s):
    return datetime.time(*[int(x) for x in s.split(':')]) if s else None

def _time_text_to_period(t):
    (start, _, end) = t.partition('-')
    return Period(
        text_to_time(start),
        text_to_time(end)
    )

# FIXME write tests!

class Schedule(object):

    def __init__(self, root, timezone):
        assert root.tag == 'schedules'
        self.root = root
        self.timezone = timezone
        self.recurring_schedules = [
            RecurringScheduleComponent(el, timezone)
            for el in root.xpath('schedule')
            if el.xpath('start_date')
        ]

    @property
    @memoize_method
    def specific_dates(self):
        """A dict of dates -> [Period time tuples] representing exceptions
        to the base recurrence pattern."""
        ex = {}
        for sd in self.root.xpath('schedule/specific_dates/specific_date'):
            bits = unicode(sd.text).split(' ')
            date = text_to_date(bits.pop(0))
            ex.setdefault(date, []).extend([
                _time_text_to_period(t)
                for t in bits
            ])
        return ex

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

        # It's not an exception. Is it within a recurring schedule?
        return any(sched.includes(query_date, query_time) for sched in self.recurring_schedules)

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
        # This could probably be more efficient
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
        periods = []

        # Add specific_dates
        exception_dates = set()
        for exception_date, exception_times in self.specific_dates.iteritems():
            exception_dates.add(exception_date)
            if exception_date >= range_start and exception_date <= range_end:
                for exception_time in exception_times:
                    periods.append(
                        Period(
                            tz.localize(datetime.datetime.combine(exception_date, exception_time.start)),
                            tz.localize(datetime.datetime.combine(exception_date, exception_time.end))
                        )
                    )

        # Add periods from recurring schedules
        for sched in self.recurring_schedules:
            for period in sched.to_periods(infinite_limit, range_start, range_end):
                if period.start.date() not in exception_dates:
                    periods.append(period)

        periods.sort()
        return periods


class RecurringScheduleComponent(object):

    def __init__(self, root, timezone):
        assert root.tag == 'schedule'
        self.root = root
        self.timezone = timezone

    def includes(self, query_date, query_time):
        """Does this schedule include the provided time?
        query_date and query_time are date and time objects, interpreted
        in this schedule's timezone"""

        if self.start_date and query_date < self.start_date:
            return False
        if self.end_date and query_date > self.end_date:
            return False
        if query_date.weekday() not in self.weekdays:
            return False

        if not query_time:
            return True

        if query_time >= self.period.start and query_time <= self.period.end:
            return True

        return False

    def to_periods(self, infinite_limit=None,
            range_start=datetime.date.min, range_end=datetime.date.max):
        """A list of datetime tuples representing all the specific periods
        of this schedule.

        If the schedule has no end_date, you must provide an infinite_limit argument.

        range_start and range_end are datetime.date objects limiting the periods returned
        """

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

        dates = list(rrule.rrule(**kw))
        period = self.period
        tz = self.timezone

        return [
            Period(
                tz.localize(datetime.datetime.combine(date, period.start)),
                tz.localize(datetime.datetime.combine(date, period.end)) 
            ) for date in dates
        ]      

    @property
    @memoize_method
    def period(self):
        """A Period tuple representing the daily start and end time."""
        start_time = self.root.findtext('start_time')
        if start_time:
            return Period(text_to_time(start_time), text_to_time(self.root.findtext('end_time')))
        return Period(datetime.time(0, 0), datetime.time(23, 59))

    @property
    def weekdays(self):
        """A set of integers representing the weekdays the schedule recurs on,
        with Monday = 0 and Sunday = 6."""
        if not self.root.xpath('days'):
            return set(range(7))
        return set(int(d) - 1 for d in self.root.xpath('days/day/text()'))

    @property
    def start_date(self):
        """Start date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('start_date'))

    @property
    def end_date(self):
        """End date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('end_date'))        
