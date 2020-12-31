# -*- coding: utf-8 -*-

def to_letters(number):
    ''' Given a number, convert it to letters
        @number (int) '''
    # TODO: Process float numbers
    schu = ["", "UN ", "DEUX ", "TROIS ", "QUATRE ", "CINQ ", "SIX ", "SEPT ", "HUIT ", "NEUF "]
    schud = ["DIX ", "ONZE ", "DOUZE ", "TREIZE ", "QUATORZE ", "QUINZE ", "SEIZE ", "DIX SEPT ", "DIX HUIT ", "DIX NEUF "]
    schd = ["", "DIX ", "VINGT ", "TRENTE ", "QUARANTE ", "CINQUANTE ", "SOIXANTE ", "SOIXANTE ", "QUATRE VINGT ", "QUATRE VINGT "]
    s = ''
    reste = number
    i = 1000000000
    while i > 0:
        y = reste / i
        if y != 0:
            centaine = y / 100
            dizaine = (y - centaine * 100) / 10
            unite = y - centaine * 100 - dizaine * 10
            if centaine == 1:
                s += "CENT "
            elif centaine != 0:
                s += schu[centaine] + "CENT "
                if dizaine == 0 and unite == 0:
                    s = s[:-1] + "S "
            if dizaine not in [0, 1]:
                s += schd[dizaine]
            if unite == 0:
                if dizaine in [1, 7, 9]:
                    s += "DIX "
                elif dizaine == 8:
                    s = s[:-1] + "S "
            elif unite == 1:
                if dizaine in [1, 9]:
                    s += "ONZE "
                elif dizaine == 7:
                    s += "ET ONZE "
                elif dizaine in [2, 3, 4, 5, 6]:
                    s += "ET UN "
                elif dizaine in [0, 8]:
                    s += "UN "
            elif unite in [2, 3, 4, 5, 6, 7, 8, 9]:
                if dizaine in [1, 7, 9]:
                    s += schud[unite]
                else:
                    s += schu[unite]
            if i == 1000000000:
                if y > 1:
                    s += "MILLIARDS "
                else:
                    s += "MILLIARD "
            if i == 1000000:
                if y > 1:
                    s += "MILLIONS "
                else:
                    s += "MILLIONS "
            if i == 1000:
                s += "MILLE "
        reste -= y * i
        i /= 1000
    if len(s) == 0:
        s += "ZERO "
    return s
