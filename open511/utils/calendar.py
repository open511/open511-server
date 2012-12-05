from collections import namedtuple
import datetime

from dateutil import rrule

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

# FIXME write tests!

class Schedule(object):

    WEEKDAYS = {
        'MO': 0,
        'TU': 1,
        'WE': 2,
        'TH': 3,
        'FR': 4,
        'SA': 5,
        'SU': 6
    }

    def __init__(self, root):
        assert root.tag == 'schedule'
        self.root = root

    @property
    @memoize_method
    def specific_dates(self):
        """A dict of dates -> Period time tuples representing exceptions
        to the base recurrence pattern."""
        ex = {}
        for sd in self.root.xpath('specificDates/specificDate'):
            d = text_to_date(sd.findtext('date'))
            ex.setdefault(d, []).extend([
                _time_el_to_period(t)
                for t in sd.xpath('times/time')
            ])
        return ex

    def includes(self, query):
        """Does this schedule include the provided datetime or date?"""
        if isinstance(query, datetime.date):
            query_date = query
            query_time = None
        else:
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
        which are datetime or date objects?"""

        if isinstance(query_start, datetime.date):
            query_start = datetime.datetime.combine(query_start, datetime.time(0, 0))
        if isinstance(query_start, datetime.date):
            query_start = datetime.datetime.combine(query_start, datetime.time(0, 0))

        for range in self.to_periods(range_start=query_start.date(), range_end=query_end.date()):
            if ((query_start <= range.start <= query_end)
                    or (query_start <= range.end <= query_end)):
                return True
        return False

    def to_periods(self, infinite_limit=None,
            range_start=datetime.date.min, range_end=datetime.date.max):
        """A list of datetime tuples representing all the periods for which
        this event is active.

        If the event has no end_date, you must provide an infinite_limit argument.

        range_start and range_end are datetime.date objects limiting the periods returned
        """

        def _combine(base, periods):
            return [
                Period(
                    datetime.datetime.combine(base, period.start),
                    datetime.datetime.combine(base, period.end)
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
                if range_end < datetime.datetime.max:
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
        return text_to_date(self.root.findtext('startDate'))

    @property
    def end_date(self):
        """End date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('endDate'))

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
        wd = self.root.findtext('daysOfWeek')
        if not wd:
            return set(range(7))
        days = set()
        for day in wd.split(','):
            try:
                days.add(self.WEEKDAYS[day])
            except KeyError:
                pass
        return days

