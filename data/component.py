from os.path import join
from collections import defaultdict, Counter

from data.utils import nucleotidesToStr


def connectedComponentsByOffset(significantReads, threshold):
    """
    Yield sets of reads that are connected according to what significant
    offsets they cover (the nucleotides at those offsets are irrelevant at
    this point).

    @param significantReads: A C{set} of C{AlignedRead} instances, all of
        which cover at least one significant offset.
    @param threshold: A C{float} indicating what fraction of read's nucleotides
        must be identical (to those already in the component) for it to be
        allowed to join a growing component.
    @return: A generator that yields C{ComponentByOffsets} instances.
    """
    while significantReads:
        element = significantReads.pop()
        component = {element}
        offsets = set(element.significantOffsets)
        addedSomething = True
        while addedSomething:
            addedSomething = False
            these = set()
            for read in significantReads:
                if offsets.intersection(read.significantOffsets):
                    addedSomething = True
                    these.add(read)
                    offsets.update(read.significantOffsets)
            if these:
                significantReads.difference_update(these)
                component.update(these)
        yield ComponentByOffsets(component, offsets, threshold)


class ConsistentComponent(object):
    """
    Hold information about a set of reads that share significant offsets
    and which (largely) agree on the nucleotides present at those offsets.
    """
    def __init__(self, reads, nucleotides):
        self.reads = reads
        self.nucleotides = nucleotides

    def __len__(self):
        return len(self.reads)

    def saveFasta(self, fp):
        for read in sorted(self.reads):
            print(read.toString(), end='', file=fp)

    def summarize(self, fp, count):
        plural = '' if len(self.reads) == 1 else 's'
        print('    Consistent component %d, %d read%s, covering %d offset%s)' %
              (count, len(self.reads), plural, len(self.nucleotides),
               '' if len(self.nucleotides) == 1 else 's'), file=fp)
        print('    Nucleotides for each offset:', file=fp)
        print(nucleotidesToStr(self.nucleotides, '      '), file=fp)
        print('    Read%s:' % plural, file=fp)
        for read in sorted(self.reads):
            print(read, file=fp)


class ComponentByOffsets(object):
    """
    Hold information about a set of reads that share significant offsets
    regardless of the nucleotides present at those offsets. Create a list
    of subsets of these reads (ConsistentComponent instances) that are
    consistent in the nucleotides at their offsets.
    """
    def __init__(self, reads, offsets, threshold):
        self.reads = reads
        self.offsets = offsets
        self.threshold = threshold
        self.consistentComponents = list(self._findConsistentComponents())
        self._check()

    def __len__(self):
        return len(self.reads)

    def _check(self):
        selfReads = len(self)
        ccReads = sum(map(len, self.consistentComponents))
        assert selfReads == ccReads, '%d != %d' % (selfReads, ccReads)

    def summarize(self, fp, count):
        print('component %d: %d reads, covering %d offsets' % (
            count, len(self), len(self.offsets)), file=fp)
        print('  offsets:', ', '.join(map(str, sorted(self.offsets))), file=fp)
        for read in sorted(self.reads):
            print('  ', read, file=fp)

        for i, cc in enumerate(self.consistentComponents, start=1):
            cc.summarize(fp, i)

    def saveFasta(self, outputDir, count):
        for i, cc in enumerate(self.consistentComponents, start=1):
            filename = join(outputDir, 'component-%d-%d.fasta' % (count, i))
            with open(filename, 'w') as fp:
                cc.saveFasta(fp)

    def _findConsistentComponents(self):
        """
        Find sets of reads that are consistent (up to the difference threshold
        in self.threshold) according to what nucleotides they have at their
        significant offsets.
        """
        def key(read):
            """
            We'll sort the avaialable reads by the number of significant
            offsets they have, then by start offset in the genome.
            """
            return (len(read.significantOffsets), read.offset)

        threshold = self.threshold

        # Take a copy of self.reads so we don't empty it.
        componentReads = set(self.reads)

        while componentReads:
            reads = sorted(componentReads, key=key, reverse=True)
            read0 = reads[0]
            these = {read0}
            nucleotides = defaultdict(Counter)
            for offset in read0.significantOffsets:
                nucleotides[offset][read0.base(offset)] += 1
            rejected = set()

            # First phase:
            #
            # Add all the reads that agree exactly at all the offsets in the
            # set so far.
            for read in reads[1:]:
                nucleotidesIfAccepted = []
                for offset in read.significantOffsets:
                    base = read.base(offset)
                    if offset in nucleotides:
                        if base not in nucleotides[offset]:
                            # Not an exact match. Reject this read for now.
                            rejected.add(read)
                            break
                    nucleotidesIfAccepted.append((offset, base))
                else:
                    # We didn't break, so add this read.
                    for offset, base in nucleotidesIfAccepted:
                        nucleotides[offset][base] += 1
                    reads.remove(read)
                    these.add(read)

            # Second phase, part 1.
            #
            # Add in the first-round rejects that have a high enough threshold.
            # We do this before we add the bases of the rejects to nucleotides
            # because we don't want to pollute 'nucleotides' with a bunch of
            # bases from first-round rejects (because their bases could
            # overwhelm the bases of the first round acceptees and lead to the
            # acceptance of reads that would otherwise be excluded).
            acceptedRejects = set()
            for read in rejected:
                total = matching = 0
                for offset in read.significantOffsets:
                    base = read.base(offset)
                    if offset in nucleotides:
                        total += 1
                        if base in nucleotides[offset]:
                            matching += 1
                if total and matching / total >= threshold:
                    # Looks good!
                    acceptedRejects.add(read)
                    reads.remove(read)
                    these.add(read)

            # Second phase, part 2.
            #
            # Add the nucleotides of the second-round acceptances.
            for accepted in acceptedRejects:
                for offset in accepted.significantOffsets:
                    nucleotides[offset][accepted.base(offset)] += 1

            componentReads.difference_update(these)
            yield ConsistentComponent(these, nucleotides)
