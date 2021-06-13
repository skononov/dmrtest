from numpy.random import randint

attlevel = 1


def tryinl(attcode):
    global attlevel
    if attcode <= attlevel:
        return True
    else:
        return False


attrange = range(1, 64)

niter = 0

while len(attrange) > 1:
    attlevel = randint(4, 10)
    midindex = len(attrange)//2
    att = attrange[midindex]
    lastoutcome = tryinl(att)
    if lastoutcome:
        attrange = attrange[midindex:]
    else:
        attrange = attrange[:midindex]
    if len(attrange) > 0:
        print('attlevel=%d, attcode=%d, comp. outcome: %r, chosen range: %d-%d' %
              (attlevel, att, lastoutcome, attrange[0], attrange[len(attrange)-1]))
    niter += 1

print('attlevel: %d, found att: %d, number of iterations: %d, outcome(att): %r, outcome(att+1): %r' %
      (attlevel, attrange[0], niter, tryinl(attrange[0]), tryinl(attrange[0]+1)))
