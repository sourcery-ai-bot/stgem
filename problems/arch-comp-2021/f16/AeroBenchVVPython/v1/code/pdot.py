'''
Stanley Bak
Python F-16
power derivative (pdot)
'''

from rtau import rtau

def pdot(p3, p1):
    'pdot function'

    if p1 >= 50:
        if p3 >= 50:
            t = 5
            p2 = p1
        else:
            p2 = 60
            t = rtau(p2 - p3)
    elif p3 >= 50:
        t = 5
        p2 = 40
    else:
        p2 = p1
        t = rtau(p2 - p3)

    return t * (p2 - p3)
