#!/usr/bin/env python

from __future__ import division, print_function

from os.path import basename
import plotly
import plotly.graph_objs as go
from operator import itemgetter
from sklearn.metrics.cluster import entropy

from dark.reads import readClassNameToClass

from data.data import (
    AlignedRead, addCommandLineOptions, parseCommandLineOptions,
    findSignificantOffsets, gatherData)

MAX_ENTROPY = 1.3


def baseCountsToStr(counts):
    """
    @param counts: A C{counter} instance.
    """
    return ' '.join([
        ('%s:%d' % (base, counts[base])) for base in sorted(counts)])


def plotSortedMaxBaseFrequencies(
        significantOffsets, baseCountAtOffset, readCountAtOffset, outFile,
        title, histogram):
    """
    Plot the sorted maximum base frequency for each of the significant
    offsets.
    """
    frequencyInfo = []

    for offset in significantOffsets:
        count = readCountAtOffset[offset]

        sortedFreqs = [x / count for x in
                       sorted(baseCountAtOffset[offset].values(),
                              reverse=True)]

        text = ('location %d<br>' % (offset + 1) +
                ', '.join('%s: %d' % (k, v)
                          for k, v in baseCountAtOffset[offset].items()))

        frequencyInfo.append((sortedFreqs[0], text))

    if histogram:
        data = [
            go.Histogram(x=[freq for freq, _ in frequencyInfo],
                         histnorm='probability'),
        ]

        xaxis = {
            'title': 'Maximum base nucleotide frequency',
            'range': (-0.05, 1.05),
        }

        yaxis = {
            'title': 'Frequency',
            'range': (0.0, 1.0),
        }
    else:
        frequencyInfo.sort(key=itemgetter(0))

        data = [
            go.Scatter(
                x=list(range(1, len(significantOffsets) + 1)),
                y=[freq for freq, _ in frequencyInfo],
                mode='markers',
                showlegend=False,
                text=[text for _, text in frequencyInfo]),
        ]

        xmargin = max(1, int(len(significantOffsets) * 0.01))
        xaxis = {
            'title': 'Significant location maximum nucleotide frequency rank',
            'range': (-xmargin, len(significantOffsets) + xmargin),
        }

        yaxis = {
            'range': (0.0, 1.05),
            'title': 'Frequency',
        }

    layout = go.Layout(title=title, xaxis=xaxis, yaxis=yaxis)
    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename=outFile, show_link=False)


def plotBaseFrequenciesEntropy(
        significantOffsets, baseCountAtOffset, readCountAtOffset, outFile,
        title, histogram):
    """
    Plot the sorted entropy of base frequencies for each of the significant
    offsets.
    """
    entropyInfo = []

    for offset in significantOffsets:
        text = ('location %d<br>' % (offset + 1) +
                ', '.join('%s: %d' % (k, v)
                          for k, v in baseCountAtOffset[offset].items()))

        entropyInfo.append(
            (entropy(list(baseCountAtOffset[offset].elements())), text))

    assert all([ent <= MAX_ENTROPY for ent, _ in entropyInfo])

    if histogram:
        data = [
            go.Histogram(x=[ent for ent, _ in entropyInfo],
                         histnorm='probability')
        ]

        xaxis = {
            'title': 'Entropy',
            'range': (-0.05, MAX_ENTROPY),
        }

        yaxis = {
            'title': 'Frequency',
            'range': (0.0, 1.0),
        }
    else:
        entropyInfo.sort(key=itemgetter(0))

        data = [
            go.Scatter(
                x=list(range(1, len(significantOffsets) + 1)),
                y=[ent for ent, _ in entropyInfo],
                mode='markers',
                showlegend=False,
                text=[text for _, text in entropyInfo]),
        ]

        xmargin = max(1, int(len(significantOffsets) * 0.01))
        xaxis = {
            'title': ('Significant location nucleotide frequency '
                      'entropy rank'),
            'range': (-xmargin, len(significantOffsets) + xmargin),
        }

        yaxis = {
            'range': (-0.05, MAX_ENTROPY),
            'title': 'Entropy',
        }

    layout = go.Layout(title=title, xaxis=xaxis, yaxis=yaxis)
    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename=outFile, show_link=False)


def plotBaseFrequencies(significantOffsets, baseCountAtOffset,
                        readCountAtOffset, outFile, title):
    """
    Plot the (sorted) base frequencies for each of the significant offsets.
    """
    x = list(range(len(significantOffsets)))
    text = []
    freqs = (
        [], [], [], [],
    )

    for offset in significantOffsets:
        count = readCountAtOffset[offset]

        sortedFreqs = [x / count for x in
                       sorted(baseCountAtOffset[offset].values(),
                              reverse=True)]
        while len(sortedFreqs) < 4:
            sortedFreqs.append(0.0)

        for i, frequency in enumerate(sortedFreqs):
            freqs[i].append(frequency)

        text.append(
            ('location %d<br>' % (offset + 1)) +
            ', '.join('%s: %d' % (k, v)
                      for k, v in baseCountAtOffset[offset].items()))

        # print('loc %d, counts %s, freqs %s' % (offset,
        # baseCountAtOffset[offset], sortedFreqs))

    data = [
        go.Bar(x=x, y=freqs[0], showlegend=False, text=text),
        go.Bar(x=x, y=freqs[1], showlegend=False),
        go.Bar(x=x, y=freqs[2], showlegend=False),
        go.Bar(x=x, y=freqs[3], showlegend=False),
    ]
    layout = go.Layout(
        barmode='stack',
        title=title,
        xaxis={
            'title': 'Significant location index',
        },
        yaxis={
            'title': 'Nucleotide frequency',
        },
    )

    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename=outFile, show_link=False)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Analyze a set of aligned reads.')

    addCommandLineOptions(parser, 'significant-base-frequencies.html')

    parser.add_argument(
        '--sampleName',
        help='The name of the sample, to appear in the plot title.')

    parser.add_argument(
        '--verbose', action='store_true', default=False,
        help='Print verbose textual output showing read connections.')

    parser.add_argument(
        '--sortOn', choices=('max', 'entropy'), default=None,
        help=('If specified, locations will be sorted according to either the '
              'maximum nucleotide frequency or the nucleotide entropy at the '
              'location.'))

    parser.add_argument(
        '--alignmentFasta',
        help=('The filename of an optional FASTA alignment to show the base '
              'frequencies for. The significant locations will always be '
              'calculated from the aligned reads, but you can use this '
              'argument to show the frequencies from another alignment at '
              'those locations.'))

    parser.add_argument(
        '--histogram', action='store_true', default=False,
        help=('If specified and --sortOn is used, the values (according to '
              '--sortOn) will be shown in a histogram.'))

    args = parser.parse_args()

    (genome, alignedReads, readCountAtOffset,
     baseCountAtOffset, readsAtOffset) = parseCommandLineOptions(args)

    genomeLength = len(genome)

    significantOffsets = list(findSignificantOffsets(
        baseCountAtOffset, readCountAtOffset, args.minReads,
        args.homogeneousCutoff))

    print('Read %d aligned reads of length %d. '
          'Found %d significant locations.' %
          (len(alignedReads), genomeLength, len(significantOffsets)))

    if args.alignmentFasta:
        # Now we have the significant offsets from the reads aligned to
        # the consensus, read in another alignment so we can show its base
        # frequencies at those offsets.
        readClass = readClassNameToClass[args.readClass]
        if args.fasta:
            from dark.fasta import FastaReads
            reads = FastaReads(args.alignmentFasta, readClass=readClass)
        elif args.fastq:
            from dark.fastq import FastqReads
            reads = FastqReads(args.alignmentFasta, readClass=readClass)
        else:
            from dark.fasta_ss import SSFastaReads
            reads = SSFastaReads(args.alignmentFasta, readClass=readClass)

        alignedReads = [AlignedRead(read) for read in reads
                        if len(read) == genomeLength]
        print('Read %d sequences of length %d from %s.' % (
            len(alignedReads), genomeLength, args.alignmentFasta))

        altReadCountAtOffset, altBaseCountAtOffset, altReadsAtOffset = (
            gatherData(genomeLength, alignedReads))

        if args.verbose:
            # Print a comparitive summary of bases at the significant
            # offsets.
            print('Summary of significant location base frequencies:')
            for offset in significantOffsets:
                print('  ', offset + 1, 'ref:',
                      baseCountsToStr(altBaseCountAtOffset[offset]),
                      'reads:',
                      baseCountsToStr(baseCountAtOffset[offset]))

        readCountAtOffset, baseCountAtOffset, readsAtOffset = (
            altReadCountAtOffset, altBaseCountAtOffset, altReadsAtOffset)

        source = ('%d sequences from %s' %
                  (len(alignedReads), basename(args.alignmentFasta)))
    else:
        source = '%d aligned read%s' % (
            len(alignedReads), '' if len(alignedReads) == 1 else 's')

    subtitle = (
        '<br>at %d significant locations. Min %d read%s per location.<br>'
        'Locations with mode nucleotide frequency >= %.2f considered '
        'homogeneous.' %
        (len(significantOffsets), args.minReads,
         '' if args.minReads == 1 else 's', args.homogeneousCutoff))

    if args.trim:
        subtitle += ' Reads trimmed by %d base%s.' % (
            args.trim, '' if args.trim == 1 else 's')

    if args.show:
        if args.sortOn is None:
            if args.sampleName:
                title = '%s base frequencies (sorted)' % args.sampleName
            else:
                title = 'Base frequencies (sorted)'
            plotBaseFrequencies(significantOffsets, baseCountAtOffset,
                                readCountAtOffset, args.outFile,
                                title + subtitle)
        elif args.sortOn == 'max':
            if args.sampleName:
                title = '%s maximum base frequency' % args.sampleName
            else:
                title = 'Maximum base frequency'
            plotSortedMaxBaseFrequencies(
                significantOffsets, baseCountAtOffset,
                readCountAtOffset, args.outFile, title + subtitle,
                args.histogram)
        else:
            # Must be entropy (due to the 'choices' arg to the arg parser).
            assert args.sortOn == 'entropy', (
                'Unknown --sortOn value: %r' % args.sortOn)
            if args.sampleName:
                title = '%s base frequency entropy' % args.sampleName
            else:
                title = 'Base frequency entropy'
            plotBaseFrequenciesEntropy(
                significantOffsets, baseCountAtOffset,
                readCountAtOffset, args.outFile, title + subtitle,
                args.histogram)
