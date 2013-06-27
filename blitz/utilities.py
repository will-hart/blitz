__author__ = 'Will Hart'

def to_blitz_date(given_date):
    """
    Generates a blitz date string from a python datetime
    """
    return given_date.strftime("%d-%m-%Y %H:%M:%S") + "." + str(
        int(float(given_date.microsecond) / 1000))
