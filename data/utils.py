import colorlover as cl
from dark.process import Executor


def baseCountsToStr(counts):
    """
    Convert base counts to a string.

    @param counts: A C{Counter} instance.
    @return: A C{str} representation of nucleotide counts at an offset.
    """
    return ' '.join([
        ('%s:%d' % (base, counts[base])) for base in sorted(counts)])


def nucleotidesToStr(nucleotides, prefix=''):
    """
    Convert offsets and base counts to a string.

    @param nucleotides: A C{defaultdict(Counter)} instance, keyed
        by C{int} offset, with nucleotides keying the Counters.
    @param prefix: A C{str} to put at the start of each line.
    @return: A C{str} representation of the offsets and nucleotide
        counts for each.
    """
    result = []
    for offset in sorted(nucleotides):
        result.append(
            '%s%d: %s' % (prefix, offset,
                          baseCountsToStr(nucleotides[offset])))
    return '\n'.join(result)


def commonest(counts, drawBreaker, drawFp=None, drawMessage=None):
    """
    Return the key of the Counter instance that is the most common.

    @param counts: A C{Counter} instance.
    @param drawBreaker: The nucleotide base to use if there is a draw (and
        the C{drawBreaker} nucleotide is one of the drawing best nucleotides.
    @param drawFp: A file pointer to write information about draws (if any) to.
    @param drawMessage: A C{str} message to write to C{drawFp}. If the string
        contains '%(baseCounts)s' that will be replaced by a string
        representation of the base counts (in C{counts}) obtained from
        C{baseCountsToStr}. If not, the base count info will be printed after
        the message.
    @return: The C{str} nucleotide that is most common in the passed C{counts}
        if there is a draw and the most common nucleotides includes
        C{drawBreaker}, return C{drawBreaker}.
    """
    orderedCounts = counts.most_common()

    maxCount = orderedCounts[0][1]
    best = [x for x in orderedCounts if x[1] == maxCount]

    if len(best) > 1:
        # There's a draw. Return the drawbreaker nucleotide if it's among
        # the best, else just return the first one given by most_common.
        if any(x[0] == drawBreaker for x in best):
            base = drawBreaker
        else:
            base = orderedCounts[0][0]

        if drawFp and drawMessage:
            bases = baseCountsToStr(counts)
            if drawMessage.find('%(baseCounts)s') > -1:
                print(drawMessage % {'baseCounts': bases}, file=drawFp)
            else:
                print('%s\n%s' % (drawMessage, bases), file=drawFp)

        return base
    else:
        return orderedCounts[0][0]


def fastaIdentityTable(filename, outputFilename, verbose, filename2=None):
    """
    Call fasta-identity-table.py to produce an HTML identity table
    for one or two FASTA files.

    @param filename: A C{str} file name containing FASTA.
    @param outputFilename: A C{str} file name to store the HTML output into.
    @param verbose: The C{int} verbosity level.
    @param filename2: An optional second C{str} file name containing FASTA.
    """
    colors = cl.scales['9']['seq']['GnBu']
    colorArgs = []
    for i in range(7):
        colorArgs.append('--color "%.2f %s"' %
                         (0.65 + 0.05 * i, colors[i]))

    file2arg = ('--fastaFile2 "%s"' % filename2) if filename2 else ''

    e = Executor()
    e.execute(
        'fasta-identity-table.py --showGaps --showLengths --footer '
        '--removeDescriptions %s %s < %s > %s' %
        (' '.join(colorArgs), file2arg, filename, outputFilename))
    if verbose > 1:
        for line in e.log:
            print('       ', line)
