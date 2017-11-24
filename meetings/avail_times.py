import arrow

def avail_time(busy_set: set, start: str, end: str):
    # Create range given user input time/date, append to set
    range_set = set()
    for r in arrow.Arrow.range("hour", start, end):
        range_set.add(r)

    # Get intersection of busy times set and set of possible times
    intersecton = range_set & busy_set

    available_lst = []
    for time in range_set:
        if time not in intersection:
            available_lst.append(time)

    # List will be used to flash messages to busy times
    return available_lst


