from subprocess import call
import pysam
from bameditor.common.methods import getReadStrand
# from bameditor.deal_mut.readEditor import modifyRead
import random

def _call(cmd):
    print cmd
    flag = call(cmd, shell=True)
    if flag == 0:
        return True
    else:
        raise Exception("Cmd Error: %s" % cmd)


def bamToFastq(bamFile, outPrefix, is_single):
    if not is_single:
        fq1 = outPrefix + "_1.fq"
        fq2 = outPrefix + "_2.fq"
        bamToFastq_cmd = "bedtools bamtofastq  -i %s -fq %s -fq2 %s" % (bamFile, fq1, fq2)
    else:
        fq1 = outPrefix + ".fq"
        fq2 = None
        bamToFastq_cmd = "bedtools bamtofastq  -i %s -fq %s " % (bamFile, fq1)
    print "bam to fastq start ..................................."
    _call(bamToFastq_cmd)
    print "bam to fastq end ....................................."
    return fq1, fq2


def bamToFastq_2(bamFile, outPrefix, is_single):
    fq1 = outPrefix + ".fq"
    bamToFastq_cmd = "bedtools bamtofastq  -i %s -fq %s " % (bamFile, fq1)
    print "bam to fastq start ..................................."
    _call(bamToFastq_cmd)
    print "bam to fastq end ....................................."
    return fq1


def map_bwa(ref_index, outSamFile, fq1, fq2=None, threadNum=1):
    if fq2 == None:
        mapping_cmd = "bwa mem -t %s %s %s >%s" % (threadNum, ref_index, fq1, outSamFile)
    else:
        mapping_cmd = "bwa mem -t %s %s %s %s >%s" % (threadNum, ref_index, fq1, fq2, outSamFile)
    print "mapping by bwa start ...................................."
    _call(mapping_cmd)
    print "mapping by bwa end ......................................"


def samToBam(inSamFile, outBamFile):
    # samToBam_cmd = "sambamba view -f bam -S -o %s %s" % (outBamFile, inSamFile)
    samToBam_cmd = "samtools view -bS %s > %s" % (inSamFile, outBamFile)
    _call(samToBam_cmd)


def bamSort(inBamFile, sortedBamFile_prefix, sort_key=None):
    if not sort_key:
        bamSort_cmd = "samtools sort %s %s" % (inBamFile, sortedBamFile_prefix)
    else:
        if sort_key == "name":
            bamSort_cmd = "samtools sort -n %s %s" % (inBamFile, sortedBamFile_prefix)
    print "samtools sort start................................"
    _call(bamSort_cmd)
    print "samtools sort end.................................."


def bamIndex(inBamFile):
    index_cmd = "samtools index %s" % (inBamFile)
    print "samtools index start .............................."
    _call(index_cmd)
    print "samtools index end ................................"


def remap(ref_index, inBamFile, outBamFile, aligner, is_single, sort=True, threadNum=4):
    print "remap start ......................................."
    aligner = aligner.lower()
    prefix = outBamFile.rstrip(".bam")
    if aligner == "bwa":
        # prefix = outBamFile.rstrip(".bam")
        if sort:
            inPrefix = inBamFile.rstrip(".bam")
            bamSort(inBamFile, inPrefix + ".sortByName", sort_key="name")
            bam_toConvert = inPrefix + ".sortByName.bam"
        else:
            bam_toConvert = inBamFile
        fastqPrefix = prefix + ".to"
        fq1, fq2 = bamToFastq(bam_toConvert, fastqPrefix, is_single)
        outSamFile = prefix + ".sam"
        map_bwa(ref_index, outSamFile, fq1, fq2, threadNum)
        outBamFile_tmp = prefix + ".unsorted.bam"
        samToBam(outSamFile, outBamFile_tmp)
        bamSort(outBamFile_tmp, prefix)
        bamIndex(outBamFile)
    elif aligner == "tmap":
        outBamFile_tmp = prefix + ".unsorted.bam"
        remap_tmap(ref_index, inBamFile, outBamFile_tmp, threadNum)
        bamSort(outBamFile_tmp, prefix)
        bamIndex(outBamFile)
    print "remap end .........................................."
    return outBamFile


def remap_2(ref_index, inBamFile, outBamFile, aligner, is_single, threadNum=1):
    print "remap start ......................................."
    if aligner == "bwa":
        prefix = outBamFile.rstrip(".bam")
        fastqPrefix = prefix + ".to"
        fq = bamToFastq_2(inBamFile, fastqPrefix, is_single)
        outSamFile = prefix + ".sam"
        map_bwa(ref_index, outSamFile, fq, threadNum=threadNum)
        outBamFile_tmp = prefix + ".unsorted.bam"
        samToBam(outSamFile, outBamFile_tmp)
        bamSort(outBamFile_tmp, prefix)
        bamIndex(outBamFile)
    print "remap end .........................................."
    return outBamFile


def remap_tmap(ref_index, inBamFile, outBamFile, threadNum=4):
    # print "remap start ......................................."
    mapping_cmd = "tmap mapall -n %s -f %s -r %s -i bam -s %s -o 2 -v -Y -u --prefix-exclude 5 -o 2 -J 25 --context stage1 map4" % (
        threadNum, ref_index, inBamFile, outBamFile)
    # mapping_cmd = "tmap mapall -n %s -f %s -r %s -i bam -s %s -o 1 -v -Y -u --prefix-exclude 5 " \
    #               "-o 2 -J 25 --end -repair 15 --do-repeat-clip --context stage1 map4" % \
    #               (threadNum, ref_index, inBamFile, outBamFile)
    _call(mapping_cmd)
    # print "remap end .........................................."
    return outBamFile


def bamMerge(bamList, outBamFile):
    cmd = "samtools merge -c -f %s %s" % (outBamFile, " ".join(bamList))
    _call(cmd)


def getRegionReads(inBam, regionBed, inRegionBam, outRegionBam):
    cmd = "samtools view %s -b -h -o %s -U %s -L %s" % (inBam, inRegionBam, outRegionBam, regionBed)
    _call(cmd)


def bamAddRG(editRemap, editBamReads, templateBamFile, outBamFile):
    # editRemapBam_addRG_File = tempOutDir + "/edit.remap.addRG.bam"
    head = editRemap.header
    head["RG"] = templateBamFile.header["RG"]
    addRGBam = pysam.AlignmentFile(outBamFile, 'wb', header=head)
    RG = _getRGs(templateBamFile)
    for read in editRemap.fetch():
        readName = read.query_name
        strand = getReadStrand(read)
        if readName in editBamReads:
            orig = editBamReads[readName][strand]
        else:
            orig = None
        newRead = readAddRG(read, orig, RG)
        # print newRead
        addRGBam.write(newRead)
    addRGBam.close()


def readAddRG(read, orig, RG=None):
    if RG:
        hasRG = False
        if read.tags is not None:
            for tag in read.tags:
                if tag[0] == 'RG':
                    hasRG = True

        # use RG from original read if it exists
        if orig is not None:
            if not hasRG and orig.tags is not None:
                for tag in orig.tags:
                    if tag[0] == 'RG':
                        read.tags = read.tags + [tag]
                        hasRG = True

        if not hasRG:
            # give up and add random read group from list in header (e.g. for simulated reads)
            newRG = RG[random.randint(0, len(RG) - 1)]
            read.tags = read.tags + [("RG", newRG)]
    return read

def _getRGs(bam):
    '''return list of RG IDs'''
    RG = []
    if 'RG' in bam.header:
        for headRG in bam.header['RG']:
            RG.append(headRG['ID'])
    return RG


def bamReadAddTag(bamFile, tag, outFile):
    bam = pysam.AlignmentFile(bamFile, 'rb')
    outBam = pysam.AlignmentFile(outFile, 'wb', template=bam)
    for read in bam.fetch():
        tags = read.tags
        tags.append((tag, 1))
        read.tags = tags
        outBam.write(read)
    outBam.close()
    bam.close()
