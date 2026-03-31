# Rich feature hierarchies for accurate object detection and semantic segmentation

Tech report (v5)
Ross Girshick Jeff Donahue Trevor Darrell Jitendra Malik
UC Berkeley

## Abstract

Object detection performance, as measured on the
canonical PASCAL VOC dataset, has plateaued in the last
few years. The best-performing methods are complex en-
semble systems that typically combine multiple low-level
image features with high-level context. In this paper, we
propose a simple and scalable detection algorithm that im-
proves mean average precision (mAP) by more than 30%
relative to the previous best result on VOC 2012—achieving
a mAP of 53.3%. Our approach combines two key insights:
(1) one can apply high-capacity convolutional neural net-
works (CNNs) to bottom-up region proposals in order to
localize and segment objects and (2) when labeled training
data is scarce, supervised pre-training for an auxiliary task,
followed by domain-specific fine-tuning, yields a significant
performance boost. Since we combine region proposals
with CNNs, we call our method R-CNN: Regions with CNN
features. We also compare R-CNN to OverFeat, a recently
proposed sliding-window detector based on a similar CNN
architecture. We find that R-CNN outperforms OverFeat
by a large margin on the 200-class ILSVRC2013 detection
dataset. Source code for the complete system is available at
http://www.cs.berkeley.edu/ ̃rbg/rcnn.

## Body

1. Introduction
Features matter. The last decade of progress on various
visual recognition tasks has been based considerably on the
use of SIFT [29] and HOG [7]. But if we look at perfor-
mance on the canonical visual recognition task, PASCAL
VOC object detection [15], it is generally acknowledged
that progress has been slow during 2010-2012, with small
gains obtained by building ensemble systems and employ-
ing minor variants of successful methods.
SIFT and HOG are blockwise orientation histograms,
a representation we could associate roughly with complex
cells in V1, the first cortical area in the primate visual path-
way. But we also know that recognition occurs several
stages downstream, which suggests that there might be hier-
1. Input 
image
2. Extract region 
proposals (~2k)
3. Compute 
CNN features
aeroplane? no.
...
person? yes.
tvmonitor? no.
4. Classify 
regions
warped region
 ...
CNN
R-CNN: Regions with CNN features
Figure 1: Object detection system overview. Our system (1)
takes an input image, (2) extracts around 2000 bottom-up region
proposals, (3) computes features for each proposal using a large
convolutional neural network (CNN), and then (4) classifies each
region using class-specific linear SVMs. R-CNN achieves a mean
average precision (mAP) of 53.7% on PASCAL VOC 2010. For
comparison, [39] reports 35.1% mAP using the same region pro-
posals, but with a spatial pyramid and bag-of-visual-words ap-
proach. The popular deformable part models perform at 33.4%.
On the 200-class ILSVRC2013 detection dataset, R-CNN’s
mAP is 31.4% , a large improvement over OverFeat [34], which
had the previous best result at 24.3%.
archical, multi-stage processes for computing features that
are even more informative for visual recognition.
Fukushima’s “neocognitron” [19], a biologically-
inspired hierarchical and shift-invariant model for pattern
recognition, was an early attempt at just such a process.
The neocognitron, however, lacked a supervised training
algorithm. Building on Rumelhart et al. [33], LeCun et
al. [26] showed that stochastic gradient descent via back-
propagation was effective for training convolutional neural
networks (CNNs), a class of models that extend the neocog-
nitron.
CNNs saw heavy use in the 1990s (e.g., [27]), but then
fell out of fashion with the rise of support vector machines.
In 2012, Krizhevsky et al. [25] rekindled interest in CNNs
by showing substantially higher image classification accu-
racy on the ImageNet Large Scale Visual Recognition Chal-
lenge (ILSVRC) [9, 10]. Their success resulted from train-
ing a large CNN on 1.2 million labeled images, together
with a few twists on LeCun’s CNN (e.g.,max(x, 0) rectify-
ing non-linearities and “dropout” regularization).
The significance of the ImageNet result was vigorously
1
arXiv:1311.2524v5 [cs.CV] 22 Oct 2014

debated during the ILSVRC 2012 workshop. The central
issue can be distilled to the following: To what extent do
the CNN classification results on ImageNet generalize to
object detection results on the PASCAL VOC Challenge?
We answer this question by bridging the gap between
image classification and object detection. This paper is the
first to show that a CNN can lead to dramatically higher ob-
ject detection performance on PASCAL VOC as compared
to systems based on simpler HOG-like features. To achieve
this result, we focused on two problems: localizing objects
with a deep network and training a high-capacity model
with only a small quantity of annotated detection data.
Unlike image classification, detection requires localiz-
ing (likely many) objects within an image. One approach
frames localization as a regression problem. However, work
from Szegedy et al. [38], concurrent with our own, indi-
cates that this strategy may not fare well in practice (they
report a mAP of 30.5% on VOC 2007 compared to the
58.5% achieved by our method). An alternative is to build a
sliding-window detector. CNNs have been used in this way
for at least two decades, typically on constrained object cat-
egories, such as faces [32, 40] and pedestrians [35]. In order
to maintain high spatial resolution, these CNNs typically
only have two convolutional and pooling layers. We also
considered adopting a sliding-window approach. However,
units high up in our network, which has five convolutional
layers, have very large receptive fields ( 195 × 195 pixels)
and strides (32×32 pixels) in the input image, which makes
precise localization within the sliding-window paradigm an
open technical challenge.
Instead, we solve the CNN localization problem by oper-
ating within the “recognition using regions” paradigm [21],
which has been successful for both object detection [39] and
semantic segmentation [5]. At test time, our method gener-
ates around 2000 category-independent region proposals for
the input image, extracts a fixed-length feature vector from
each proposal using a CNN, and then classifies each region
with category-specific linear SVMs. We use a simple tech-
nique (affine image warping) to compute a fixed-size CNN
input from each region proposal, regardless of the region’s
shape. Figure 1 presents an overview of our method and
highlights some of our results. Since our system combines
region proposals with CNNs, we dub the method R-CNN:
Regions with CNN features.
In this updated version of this paper, we provide a head-
to-head comparison of R-CNN and the recently proposed
OverFeat [34] detection system by running R-CNN on the
200-class ILSVRC2013 detection dataset. OverFeat uses a
sliding-window CNN for detection and until now was the
best performing method on ILSVRC2013 detection. We
show that R-CNN significantly outperforms OverFeat, with
a mAP of 31.4% versus 24.3%.
A second challenge faced in detection is that labeled data
is scarce and the amount currently available is insufficient
for training a large CNN. The conventional solution to this
problem is to useunsupervised pre-training, followed by su-
pervised fine-tuning (e.g., [35]). The second principle con-
tribution of this paper is to show thatsupervised pre-training
on a large auxiliary dataset (ILSVRC), followed by domain-
specific fine-tuning on a small dataset (PASCAL), is an
effective paradigm for learning high-capacity CNNs when
data is scarce. In our experiments, fine-tuning for detection
improves mAP performance by 8 percentage points. After
fine-tuning, our system achieves a mAP of 54% on VOC
2010 compared to 33% for the highly-tuned, HOG-based
deformable part model (DPM) [17, 20]. We also point read-
ers to contemporaneous work by Donahue et al. [12], who
show that Krizhevsky’s CNN can be used (without fine-
tuning) as a blackbox feature extractor, yielding excellent
performance on several recognition tasks including scene
classification, fine-grained sub-categorization, and domain
adaptation.
Our system is also quite efficient. The only class-specific
computations are a reasonably small matrix-vector product
and greedy non-maximum suppression. This computational
property follows from features that are shared across all cat-
egories and that are also two orders of magnitude lower-
dimensional than previously used region features (cf. [39]).
Understanding the failure modes of our approach is also
critical for improving it, and so we report results from the
detection analysis tool of Hoiem et al. [23]. As an im-
mediate consequence of this analysis, we demonstrate that
a simple bounding-box regression method significantly re-
duces mislocalizations, which are the dominant error mode.
Before developing technical details, we note that because
R-CNN operates on regions it is natural to extend it to the
task of semantic segmentation. With minor modifications,
we also achieve competitive results on the PASCAL VOC
segmentation task, with an average segmentation accuracy
of 47.9% on the VOC 2011 test set.
2. Object detection with R-CNN
Our object detection system consists of three modules.
The first generates category-independent region proposals.
These proposals define the set of candidate detections avail-
able to our detector. The second module is a large convo-
lutional neural network that extracts a fixed-length feature
vector from each region. The third module is a set of class-
specific linear SVMs. In this section, we present our design
decisions for each module, describe their test-time usage,
detail how their parameters are learned, and show detection
results on PASCAL VOC 2010-12 and on ILSVRC2013.
2.1. Module design
Region proposals. A variety of recent papers offer meth-
ods for generating category-independent region proposals.
2

aeroplane bicycle bird car
Figure 2: Warped training samples from VOC 2007 train.
Examples include: objectness [1], selective search [39],
category-independent object proposals [14], constrained
parametric min-cuts (CPMC) [5], multi-scale combinatorial
grouping [3], and Cires ̧an et al. [6], who detect mitotic cells
by applying a CNN to regularly-spaced square crops, which
are a special case of region proposals. While R-CNN is ag-
nostic to the particular region proposal method, we use se-
lective search to enable a controlled comparison with prior
detection work (e.g., [39, 41]).
Feature extraction. We extract a 4096-dimensional fea-
ture vector from each region proposal using the Caffe [24]
implementation of the CNN described by Krizhevsky et
al. [25]. Features are computed by forward propagating
a mean-subtracted 227 × 227 RGB image through five con-
volutional layers and two fully connected layers. We refer
readers to [24, 25] for more network architecture details.
In order to compute features for a region proposal, we
must first convert the image data in that region into a form
that is compatible with the CNN (its architecture requires
inputs of a fixed227 × 227 pixel size). Of the many possi-
ble transformations of our arbitrary-shaped regions, we opt
for the simplest. Regardless of the size or aspect ratio of the
candidate region, we warp all pixels in a tight bounding box
around it to the required size. Prior to warping, we dilate the
tight bounding box so that at the warped size there are ex-
actlyp pixels of warped image context around the original
box (we use p = 16 ). Figure 2 shows a random sampling
of warped training regions. Alternatives to warping are dis-
cussed in Appendix A.
2.2. Test-time detection
At test time, we run selective search on the test image
to extract around 2000 region proposals (we use selective
search’s “fast mode” in all experiments). We warp each
proposal and forward propagate it through the CNN in or-
der to compute features. Then, for each class, we score
each extracted feature vector using the SVM trained for that
class. Given all scored regions in an image, we apply a
greedy non-maximum suppression (for each class indepen-
dently) that rejects a region if it has an intersection-over-
union (IoU) overlap with a higher scoring selected region
larger than a learned threshold.
Run-time analysis. Two properties make detection effi-
cient. First, all CNN parameters are shared across all cate-
gories. Second, the feature vectors computed by the CNN
are low-dimensional when compared to other common ap-
proaches, such as spatial pyramids with bag-of-visual-word
encodings. The features used in the UV A detection system
[39], for example, are two orders of magnitude larger than
ours (360k vs. 4k-dimensional).
The result of such sharing is that the time spent com-
puting region proposals and features (13s/image on a GPU
or 53s/image on a CPU) is amortized over all classes. The
only class-specific computations are dot products between
features and SVM weights and non-maximum suppression.
In practice, all dot products for an image are batched into
a single matrix-matrix product. The feature matrix is typi-
cally 2000 × 4096 and the SVM weight matrix is4096 ×N,
whereN is the number of classes.
This analysis shows that R-CNN can scale to thousands
of object classes without resorting to approximate tech-
niques, such as hashing. Even if there were 100k classes,
the resulting matrix multiplication takes only 10 seconds on
a modern multi-core CPU. This efficiency is not merely the
result of using region proposals and shared features. The
UV A system, due to its high-dimensional features, would
be two orders of magnitude slower while requiring 134GB
of memory just to store 100k linear predictors, compared to
just 1.5GB for our lower-dimensional features.
It is also interesting to contrast R-CNN with the recent
work from Dean et al. on scalable detection using DPMs
and hashing [8]. They report a mAP of around 16% on VOC
2007 at a run-time of 5 minutes per image when introducing
10k distractor classes. With our approach, 10k detectors can
run in about a minute on a CPU, and because no approxi-
mations are made mAP would remain at 59% (Section 3.2).
2.3. Training
Supervised pre-training. We discriminatively pre-trained
the CNN on a large auxiliary dataset (ILSVRC2012 clas-
sification) using image-level annotations only (bounding-
box labels are not available for this data). Pre-training
was performed using the open source Caffe CNN library
[24]. In brief, our CNN nearly matches the performance
of Krizhevsky et al. [25], obtaining a top-1 error rate 2.2
percentage points higher on the ILSVRC2012 classification
validation set. This discrepancy is due to simplifications in
the training process.
Domain-specific fine-tuning. To adapt our CNN to the
new task (detection) and the new domain (warped proposal
windows), we continue stochastic gradient descent (SGD)
training of the CNN parameters using only warped region
proposals. Aside from replacing the CNN’s ImageNet-
specific 1000-way classification layer with a randomly ini-
tialized (N + 1)-way classification layer (where N is the
number of object classes, plus 1 for background), the CNN
architecture is unchanged. For VOC, N = 20 and for
ILSVRC2013,N = 200. We treat all region proposals with
3

≥ 0.5 IoU overlap with a ground-truth box as positives for
that box’s class and the rest as negatives. We start SGD at
a learning rate of 0.001 (1/10th of the initial pre-training
rate), which allows fine-tuning to make progress while not
clobbering the initialization. In each SGD iteration, we uni-
formly sample 32 positive windows (over all classes) and
96 background windows to construct a mini-batch of size
128. We bias the sampling towards positive windows be-
cause they are extremely rare compared to background.
Object category classifiers. Consider training a binary
classifier to detect cars. It’s clear that an image region
tightly enclosing a car should be a positive example. Simi-
larly, it’s clear that a background region, which has nothing
to do with cars, should be a negative example. Less clear
is how to label a region that partially overlaps a car. We re-
solve this issue with an IoU overlap threshold, below which
regions are defined as negatives. The overlap threshold,0.3,
was selected by a grid search over {0, 0.1,..., 0.5} on a
validation set. We found that selecting this threshold care-
fully is important. Setting it to 0.5, as in [39], decreased
mAP by 5 points. Similarly, setting it to 0 decreased mAP
by 4 points. Positive examples are defined simply to be the
ground-truth bounding boxes for each class.
Once features are extracted and training labels are ap-
plied, we optimize one linear SVM per class. Since the
training data is too large to fit in memory, we adopt the
standard hard negative mining method [17, 37]. Hard neg-
ative mining converges quickly and in practice mAP stops
increasing after only a single pass over all images.
In Appendix B we discuss why the positive and negative
examples are defined differently in fine-tuning versus SVM
training. We also discuss the trade-offs involved in training
detection SVMs rather than simply using the outputs from
the final softmax layer of the fine-tuned CNN.
2.4. Results on PASCAL VOC 2010-12
Following the PASCAL VOC best practices [15], we
validated all design decisions and hyperparameters on the
VOC 2007 dataset (Section 3.2). For final results on the
VOC 2010-12 datasets, we fine-tuned the CNN on VOC
2012 train and optimized our detection SVMs on VOC 2012
trainval. We submitted test results to the evaluation server
only once for each of the two major algorithm variants (with
and without bounding-box regression).
Table 1 shows complete results on VOC 2010. We com-
pare our method against four strong baselines, including
SegDPM [18], which combines DPM detectors with the
output of a semantic segmentation system [4] and uses ad-
ditional inter-detector context and image-classifier rescor-
ing. The most germane comparison is to the UV A system
from Uijlings et al. [39], since our systems use the same re-
gion proposal algorithm. To classify regions, their method
builds a four-level spatial pyramid and populates it with
densely sampled SIFT, Extended OpponentSIFT, and RGB-
SIFT descriptors, each vector quantized with 4000-word
codebooks. Classification is performed with a histogram
intersection kernel SVM. Compared to their multi-feature,
non-linear kernel SVM approach, we achieve a large im-
provement in mAP, from 35.1% to 53.7% mAP, while also
being much faster (Section 2.2). Our method achieves sim-
ilar performance (53.3% mAP) on VOC 2011/12 test.
2.5. Results on ILSVRC2013 detection
We ran R-CNN on the 200-class ILSVRC2013 detection
dataset using the same system hyperparameters that we used
for PASCAL VOC. We followed the same protocol of sub-
mitting test results to the ILSVRC2013 evaluation server
only twice, once with and once without bounding-box re-
gression.
Figure 3 compares R-CNN to the entries in the ILSVRC
2013 competition and to the post-competition OverFeat re-
sult [34]. R-CNN achieves a mAP of 31.4%, which is sig-
nificantly ahead of the second-best result of 24.3% from
OverFeat. To give a sense of the AP distribution over
classes, box plots are also presented and a table of per-
class APs follows at the end of the paper in Table 8. Most
of the competing submissions (OverFeat, NEC-MU, UvA-
Euvision, Toronto A, and UIUC-IFP) used convolutional
neural networks, indicating that there is significant nuance
in how CNNs can be applied to object detection, leading to
greatly varying outcomes.
In Section 4, we give an overview of the ILSVRC2013
detection dataset and provide details about choices that we
made when running R-CNN on it.
3. Visualization, ablation, and modes of error
3.1. Visualizing learned features
First-layer filters can be visualized directly and are easy
to understand [25]. They capture oriented edges and oppo-
nent colors. Understanding the subsequent layers is more
challenging. Zeiler and Fergus present a visually attrac-
tive deconvolutional approach in [42]. We propose a simple
(and complementary) non-parametric method that directly
shows what the network learned.
The idea is to single out a particular unit (feature) in the
network and use it as if it were an object detector in its own
right. That is, we compute the unit’s activations on a large
set of held-out region proposals (about 10 million), sort the
proposals from highest to lowest activation, perform non-
maximum suppression, and then display the top-scoring re-
gions. Our method lets the selected unit “speak for itself”
by showing exactly which inputs it fires on. We avoid aver-
aging in order to see different visual modes and gain insight
into the invariances computed by the unit.
4

VOC 2010 testaero bike bird boat bottle bus car cat chair cow table dog horse mbike person plant sheep sofa train tv mAP
DPM v5 [20]† 49.2 53.8 13.1 15.3 35.5 53.4 49.7 27.0 17.2 28.8 14.7 17.8 46.4 51.2 47.7 10.8 34.2 20.7 43.8 38.3 33.4
UV A [39] 56.2 42.4 15.3 12.6 21.8 49.3 36.8 46.1 12.9 32.1 30.0 36.5 43.5 52.9 32.9 15.3 41.1 31.8 47.0 44.8 35.1
Regionlets [41]65.0 48.9 25.9 24.6 24.5 56.1 54.5 51.2 17.0 28.9 30.2 35.8 40.2 55.7 43.5 14.3 43.9 32.6 54.0 45.9 39.7
SegDPM [18]† 61.4 53.4 25.6 25.2 35.5 51.7 50.6 50.8 19.3 33.8 26.8 40.4 48.3 54.4 47.1 14.8 38.7 35.0 52.8 43.1 40.4
R-CNN 67.1 64.1 46.7 32.0 30.5 56.4 57.2 65.9 27.0 47.3 40.9 66.6 57.8 65.9 53.6 26.7 56.5 38.1 52.8 50.2 50.2
R-CNN BB 71.8 65.8 53.0 36.8 35.9 59.7 60.0 69.9 27.9 50.6 41.4 70.0 62.0 69.0 58.1 29.5 59.4 39.3 61.2 52.4 53.7
Table 1: Detection average precision (%) on VOC 2010 test. R-CNN is most directly comparable to UV A and Regionlets since all
methods use selective search region proposals. Bounding-box regression (BB) is described in Section C. At publication time, SegDPM
was the top-performer on the PASCAL VOC leaderboard. †DPM and SegDPM use context rescoring not used by the other methods.
0 20 40 60 80 100
UIUC−IFP 
Delta 
GPU_UCLA 
SYSU_Vision 
Toronto A 
*OverFeat (1) 
*NEC−MU 
UvA−Euvision 
*OverFeat (2) 
*R−CNN BB 
mean average precision (mAP) in %
ILSVRC2013 detection test set mAP
 
 
1.0%
6.1%
9.8%
10.5%
11.5%
19.4%
20.9%
22.6%
24.3%
31.4%
competition result
post competition result
0
10
20
30
40
50
60
70
80
90
100
*R−CNN BB
UvA−Euvision
*NEC−MU
*OverFeat (1)
Toronto A
SYSU_Vision
GPU_UCLA
Delta
UIUC−IFP
average precision (AP) in %
ILSVRC2013 detection test set class AP box plots
Figure 3: (Left) Mean average precision on the ILSVRC2013 detection test set. Methods preceeded by * use outside training data
(images and labels from the ILSVRC classification dataset in all cases). (Right) Box plots for the 200 average precision values per
method. A box plot for the post-competition OverFeat result is not shown because per-class APs are not yet available (per-class APs for
R-CNN are in Table 8 and also included in the tech report source uploaded to arXiv.org; seeR-CNN-ILSVRC2013-APs.txt). The red
line marks the median AP, the box bottom and top are the 25th and 75th percentiles. The whiskers extend to the min and max AP of each
method. Each AP is plotted as a green dot over the whiskers (best viewed digitally with zoom).
1.0 1.0 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9 0.9
1.0 0.9 0.9 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6
1.0 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6
1.0 0.9 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
1.0 1.0 0.9 0.9 0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8
1.0 0.9 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
Figure 4: Top regions for six pool5 units. Receptive fields and activation values are drawn in white. Some units are aligned to concepts,
such as people (row 1) or text (4). Other units capture texture and material properties, such as dot arrays (2) and specular reflections (6).
5

VOC 2007 test aero bike bird boat bottle bus car cat chair cow table dog horse mbike person plant sheep sofa train tv mAP
R-CNN pool5 51.8 60.2 36.4 27.8 23.2 52.8 60.6 49.2 18.3 47.8 44.3 40.8 56.6 58.7 42.4 23.4 46.1 36.7 51.3 55.7 44.2
R-CNN fc6 59.3 61.8 43.1 34.0 25.1 53.1 60.6 52.8 21.7 47.8 42.7 47.8 52.5 58.5 44.6 25.6 48.3 34.0 53.1 58.0 46.2
R-CNN fc7 57.6 57.9 38.5 31.8 23.7 51.2 58.9 51.4 20.0 50.5 40.9 46.0 51.6 55.9 43.3 23.3 48.1 35.3 51.0 57.4 44.7
R-CNN FT pool5 58.2 63.3 37.9 27.6 26.1 54.1 66.9 51.4 26.7 55.5 43.4 43.1 57.7 59.0 45.8 28.1 50.8 40.6 53.1 56.4 47.3
R-CNN FT fc6 63.5 66.0 47.9 37.7 29.9 62.5 70.2 60.2 32.0 57.9 47.0 53.5 60.1 64.2 52.2 31.3 55.0 50.0 57.7 63.0 53.1
R-CNN FT fc7 64.2 69.7 50.0 41.9 32.0 62.6 71.0 60.7 32.7 58.5 46.5 56.1 60.6 66.8 54.2 31.5 52.8 48.9 57.9 64.7 54.2
R-CNN FT fc7 BB 68.1 72.8 56.8 43.0 36.8 66.3 74.2 67.6 34.4 63.5 54.5 61.2 69.1 68.6 58.7 33.4 62.9 51.1 62.5 64.8 58.5
DPM v5 [20] 33.2 60.3 10.2 16.1 27.3 54.3 58.2 23.0 20.0 24.1 26.7 12.7 58.1 48.2 43.2 12.0 21.1 36.1 46.0 43.5 33.7
DPM ST [28] 23.8 58.2 10.5 8.5 27.1 50.4 52.0 7.3 19.2 22.8 18.1 8.0 55.9 44.8 32.4 13.3 15.9 22.8 46.2 44.9 29.1
DPM HSC [31] 32.2 58.3 11.5 16.3 30.6 49.9 54.8 23.5 21.5 27.7 34.0 13.7 58.1 51.6 39.9 12.4 23.5 34.4 47.4 45.2 34.3
Table 2: Detection average precision (%) on VOC 2007 test. Rows 1-3 show R-CNN performance without fine-tuning. Rows 4-6 show
results for the CNN pre-trained on ILSVRC 2012 and then fine-tuned (FT) on VOC 2007 trainval. Row 7 includes a simple bounding-box
regression (BB) stage that reduces localization errors (Section C). Rows 8-10 present DPM methods as a strong baseline. The first uses
only HOG, while the next two use different feature learning approaches to augment or replace HOG.
VOC 2007 test aero bike bird boat bottle bus car cat chair cow table dog horse mbike person plant sheep sofa train tv mAP
R-CNN T-Net 64.2 69.7 50.0 41.9 32.0 62.6 71.0 60.7 32.7 58.5 46.5 56.1 60.6 66.8 54.2 31.5 52.8 48.9 57.9 64.7 54.2
R-CNN T-Net BB68.1 72.8 56.8 43.0 36.8 66.3 74.2 67.6 34.4 63.5 54.5 61.2 69.1 68.6 58.7 33.4 62.9 51.1 62.5 64.8 58.5
R-CNN O-Net 71.6 73.5 58.1 42.2 39.4 70.7 76.0 74.5 38.7 71.0 56.9 74.5 67.9 69.6 59.3 35.7 62.1 64.0 66.5 71.2 62.2
R-CNN O-Net BB73.4 77.0 63.4 45.4 44.6 75.1 78.1 79.8 40.5 73.7 62.2 79.4 78.1 73.1 64.2 35.6 66.8 67.2 70.4 71.1 66.0
Table 3: Detection average precision (%) on VOC 2007 test for two different CNN architectures. The first two rows are results from
Table 2 using Krizhevsky et al.’s architecture (T-Net). Rows three and four use the recently proposed 16-layer architecture from Simonyan
and Zisserman (O-Net) [43].
We visualize units from layer pool 5, which is the max-
pooled output of the network’s fifth and final convolutional
layer. The pool 5 feature map is 6 × 6 × 256 = 9216 -
dimensional. Ignoring boundary effects, each pool5 unit has
a receptive field of195×195 pixels in the original227×227
pixel input. A central pool 5 unit has a nearly global view,
while one near the edge has a smaller, clipped support.
Each row in Figure 4 displays the top 16 activations for
a pool5 unit from a CNN that we fine-tuned on VOC 2007
trainval. Six of the 256 functionally unique units are visu-
alized (Appendix D includes more). These units were se-
lected to show a representative sample of what the network
learns. In the second row, we see a unit that fires on dog
faces and dot arrays. The unit corresponding to the third row
is a red blob detector. There are also detectors for human
faces and more abstract patterns such as text and triangular
structures with windows. The network appears to learn a
representation that combines a small number of class-tuned
features together with a distributed representation of shape,
texture, color, and material properties. The subsequent fully
connected layer fc 6 has the ability to model a large set of
compositions of these rich features.
3.2. Ablation studies
Performance layer-by-layer, without fine-tuning. To un-
derstand which layers are critical for detection performance,
we analyzed results on the VOC 2007 dataset for each of the
CNN’s last three layers. Layer pool 5 was briefly described
in Section 3.1. The final two layers are summarized below.
Layer fc6 is fully connected to pool 5. To compute fea-
tures, it multiplies a4096×9216 weight matrix by the pool5
feature map (reshaped as a 9216-dimensional vector) and
then adds a vector of biases. This intermediate vector is
component-wise half-wave rectified (x ← max(0,x )).
Layer fc 7 is the final layer of the network. It is imple-
mented by multiplying the features computed by fc 6 by a
4096 × 4096 weight matrix, and similarly adding a vector
of biases and applying half-wave rectification.
We start by looking at results from the CNN without
fine-tuning on PASCAL, i.e. all CNN parameters were
pre-trained on ILSVRC 2012 only. Analyzing performance
layer-by-layer (Table 2 rows 1-3) reveals that features from
fc7 generalize worse than features from fc 6. This means
that 29%, or about 16.8 million, of the CNN’s parameters
can be removed without degrading mAP. More surprising is
that removing both fc7 and fc6 produces quite good results
even though pool5 features are computed using only 6% of
the CNN’s parameters. Much of the CNN’s representational
power comes from its convolutional layers, rather than from
the much larger densely connected layers. This finding sug-
gests potential utility in computing a dense feature map, in
the sense of HOG, of an arbitrary-sized image by using only
the convolutional layers of the CNN. This representation
would enable experimentation with sliding-window detec-
tors, including DPM, on top of pool5 features.
Performance layer-by-layer, with fine-tuning. We now
look at results from our CNN after having fine-tuned its pa-
6

rameters on VOC 2007 trainval. The improvement is strik-
ing (Table 2 rows 4-6): fine-tuning increases mAP by 8.0
percentage points to 54.2%. The boost from fine-tuning is
much larger for fc 6 and fc7 than for pool 5, which suggests
that the pool 5 features learned from ImageNet are general
and that most of the improvement is gained from learning
domain-specific non-linear classifiers on top of them.
Comparison to recent feature learning methods. Rela-
tively few feature learning methods have been tried on PAS-
CAL VOC detection. We look at two recent approaches that
build on deformable part models. For reference, we also in-
clude results for the standard HOG-based DPM [20].
The first DPM feature learning method, DPM ST [28],
augments HOG features with histograms of “sketch token”
probabilities. Intuitively, a sketch token is a tight distri-
bution of contours passing through the center of an image
patch. Sketch token probabilities are computed at each pixel
by a random forest that was trained to classify35 × 35 pixel
patches into one of 150 sketch tokens or background.
The second method, DPM HSC [31], replaces HOG with
histograms of sparse codes (HSC). To compute an HSC,
sparse code activations are solved for at each pixel using
a learned dictionary of 100 7 × 7 pixel (grayscale) atoms.
The resulting activations are rectified in three ways (full and
both half-waves), spatially pooled, unit l2 normalized, and
then power transformed (x ← sign(x)|x|α).
All R-CNN variants strongly outperform the three DPM
baselines (Table 2 rows 8-10), including the two that use
feature learning. Compared to the latest version of DPM,
which uses only HOG features, our mAP is more than 20
percentage points higher: 54.2% vs. 33.7%— a 61% rela-
tive improvement. The combination of HOG and sketch to-
kens yields 2.5 mAP points over HOG alone, while HSC
improves over HOG by 4 mAP points (when compared
internally to their private DPM baselines—both use non-
public implementations of DPM that underperform the open
source version [20]). These methods achieve mAPs of
29.1% and 34.3%, respectively.
3.3. Network architectures
Most results in this paper use the network architecture
from Krizhevsky et al. [25]. However, we have found that
the choice of architecture has a large effect on R-CNN de-
tection performance. In Table 3 we show results on VOC
2007 test using the 16-layer deep network recently proposed
by Simonyan and Zisserman [43]. This network was one of
the top performers in the recent ILSVRC 2014 classifica-
tion challenge. The network has a homogeneous structure
consisting of 13 layers of 3 × 3 convolution kernels, with
five max pooling layers interspersed, and topped with three
fully-connected layers. We refer to this network as “O-Net”
for OxfordNet and the baseline as “T-Net” for TorontoNet.
To use O-Net in R-CNN, we downloaded the pub-
licly available pre-trained network weights for the
VGG ILSVRC 16 layers model from the Caffe Model
Zoo.1 We then fine-tuned the network using the same pro-
tocol as we used for T-Net. The only difference was to use
smaller minibatches (24 examples) as required in order to
fit within GPU memory. The results in Table 3 show that R-
CNN with O-Net substantially outperforms R-CNN with T-
Net, increasing mAP from 58.5% to 66.0%. However there
is a considerable drawback in terms of compute time, with
the forward pass of O-Net taking roughly 7 times longer
than T-Net.
3.4. Detection error analysis
We applied the excellent detection analysis tool from
Hoiem et al. [23] in order to reveal our method’s error
modes, understand how fine-tuning changes them, and to
see how our error types compare with DPM. A full sum-
mary of the analysis tool is beyond the scope of this pa-
per and we encourage readers to consult [23] to understand
some finer details (such as “normalized AP”). Since the
analysis is best absorbed in the context of the associated
plots, we present the discussion within the captions of Fig-
ure 5 and Figure 6.
3.5. Bounding-box regression
Based on the error analysis, we implemented a sim-
ple method to reduce localization errors. Inspired by the
bounding-box regression employed in DPM [17], we train a
linear regression model to predict a new detection window
given the pool 5 features for a selective search region pro-
posal. Full details are given in Appendix C. Results in Ta-
ble 1, Table 2, and Figure 5 show that this simple approach
fixes a large number of mislocalized detections, boosting
mAP by 3 to 4 points.
3.6. Qualitative results
Qualitative detection results on ILSVRC2013 are pre-
sented in Figure 8 and Figure 9 at the end of the paper. Each
image was sampled randomly from the val 2 set and all de-
tections from all detectors with a precision greater than 0.5
are shown. Note that these are not curated and give a re-
alistic impression of the detectors in action. More qualita-
tive results are presented in Figure 10 and Figure 11, but
these have been curated. We selected each image because it
contained interesting, surprising, or amusing results. Here,
also, all detections at precision greater than 0.5 are shown.
4. The ILSVRC2013 detection dataset
In Section 2 we presented results on the ILSVRC2013
detection dataset. This dataset is less homogeneous than
1https://github.com/BVLC/caffe/wiki/Model-Zoo
7

occ trn size asp view part0
0.2
0.4
0.6
0.8
0.212
0.612
0.420
0.557
0.201
0.720
0.344
0.606
0.351
0.677
0.244
0.609
0.516
normalized AP
R−CNN fc6: sensitivity and impact
occ trn size asp view part0
0.2
0.4
0.6
0.8
0.179
0.701
0.498
0.634
0.335
0.766
0.442
0.672
0.429
0.723
0.325
0.685
0.593
normalized AP
R−CNN FT fc7: sensitivity and impact
occ trn size asp view part0
0.2
0.4
0.6
0.8
0.211
0.731
0.542
0.676
0.385
0.786
0.484
0.709
0.453
0.779
0.368
0.720
0.633
normalized AP
R−CNN FT fc7 BB: sensitivity and impact
occ trn size asp view part0
0.2
0.4
0.6
0.8
0.132
0.339
0.216
0.347
0.056
0.487
0.126
0.453
0.137
0.391
0.094
0.388
0.297
normalized AP
DPM voc−release5: sensitivity and impact
Figure 6: Sensitivity to object characteristics. Each plot shows the mean (over classes) normalized AP (see [23]) for the highest and
lowest performing subsets within six different object characteristics (occlusion, truncation, bounding-box area, aspect ratio, viewpoint, part
visibility). We show plots for our method (R-CNN) with and without fine-tuning (FT) and bounding-box regression (BB) as well as for
DPM voc-release5. Overall, fine-tuning does not reduce sensitivity (the difference between max and min), but does substantially improve
both the highest and lowest performing subsets for nearly all characteristics. This indicates that fine-tuning does more than simply improve
the lowest performing subsets for aspect ratio and bounding-box area, as one might conjecture based on how we warp network inputs.
Instead, fine-tuning improves robustness for all characteristics including occlusion, truncation, viewpoint, and part visibility.
total false positives
percentage of each type
R−CNN fc6: animals
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
total false positives
percentage of each type
R−CNN FT fc7: animals
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
total false positives
percentage of each type
R−CNN FT fc7 BB: animals
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
total false positives
percentage of each type
R−CNN fc6: furniture
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
total false positives
percentage of each type
R−CNN FT fc7: furniture
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
total false positives
percentage of each type
R−CNN FT fc7 BB: furniture
 
 
25 100 400 1600 64000
20
40
60
80
100
Loc
Sim
Oth
BG
Figure 5: Distribution of top-ranked false positive (FP) types.
Each plot shows the evolving distribution of FP types as more FPs
are considered in order of decreasing score. Each FP is catego-
rized into 1 of 4 types: Loc—poor localization (a detection with
an IoU overlap with the correct class between 0.1 and 0.5, or a du-
plicate); Sim—confusion with a similar category; Oth—confusion
with a dissimilar object category; BG—a FP that fired on back-
ground. Compared with DPM (see [23]), significantly more of
our errors result from poor localization, rather than confusion with
background or other object classes, indicating that the CNN fea-
tures are much more discriminative than HOG. Loose localiza-
tion likely results from our use of bottom-up region proposals and
the positional invariance learned from pre-training the CNN for
whole-image classification. Column three shows how our simple
bounding-box regression method fixes many localization errors.
PASCAL VOC, requiring choices about how to use it. Since
these decisions are non-trivial, we cover them in this sec-
tion.
4.1. Dataset overview
The ILSVRC2013 detection dataset is split into three
sets: train (395,918), val (20,121), and test (40,152), where
the number of images in each set is in parentheses. The
val and test splits are drawn from the same image distribu-
tion. These images are scene-like and similar in complexity
(number of objects, amount of clutter, pose variability, etc.)
to PASCAL VOC images. The val and test splits are exhaus-
tively annotated, meaning that in each image all instances
from all 200 classes are labeled with bounding boxes. The
train set, in contrast, is drawn from the ILSVRC2013 clas-
sification image distribution. These images have more vari-
able complexity with a skew towards images of a single cen-
tered object. Unlike val and test, the train images (due to
their large number) are not exhaustively annotated. In any
given train image, instances from the 200 classes may or
may not be labeled. In addition to these image sets, each
class has an extra set of negative images. Negative images
are manually checked to validate that they do not contain
any instances of their associated class. The negative im-
age sets were not used in this work. More information on
how ILSVRC was collected and annotated can be found in
[11, 36].
The nature of these splits presents a number of choices
for training R-CNN. The train images cannot be used for
hard negative mining, because annotations are not exhaus-
tive. Where should negative examples come from? Also,
the train images have different statistics than val and test.
Should the train images be used at all, and if so, to what
extent? While we have not thoroughly evaluated a large
number of choices, we present what seemed like the most
obvious path based on previous experience.
Our general strategy is to rely heavily on the val set and
use some of the train images as an auxiliary source of pos-
itive examples. To use val for both training and valida-
tion, we split it into roughly equally sized “val1” and “val 2”
sets. Since some classes have very few examples in val (the
smallest has only 31 and half have fewer than 110), it is
important to produce an approximately class-balanced par-
tition. To do this, a large number of candidate splits were
generated and the one with the smallest maximum relative
8

class imbalance was selected. 2 Each candidate split was
generated by clustering val images using their class counts
as features, followed by a randomized local search that may
improve the split balance. The particular split used here has
a maximum relative imbalance of about 11% and a median
relative imbalance of 4%. The val1/val2 split and code used
to produce them will be publicly available to allow other re-
searchers to compare their methods on the val splits used in
this report.
4.2. Region proposals
We followed the same region proposal approach that was
used for detection on PASCAL. Selective search [39] was
run in “fast mode” on each image in val1, val2, and test (but
not on images in train). One minor modification was re-
quired to deal with the fact that selective search is not scale
invariant and so the number of regions produced depends
on the image resolution. ILSVRC image sizes range from
very small to a few that are several mega-pixels, and so we
resized each image to a fixed width (500 pixels) before run-
ning selective search. On val, selective search resulted in an
average of 2403 region proposals per image with a 91.6%
recall of all ground-truth bounding boxes (at 0.5 IoU thresh-
old). This recall is notably lower than in PASCAL, where
it is approximately 98%, indicating significant room for im-
provement in the region proposal stage.
4.3. Training data
For training data, we formed a set of images and boxes
that includes all selective search and ground-truth boxes
from val 1 together with up to N ground-truth boxes per
class from train (if a class has fewer than N ground-truth
boxes in train, then we take all of them). We’ll call this
dataset of images and boxes val 1+trainN . In an ablation
study, we show mAP on val2 forN ∈ {0, 500, 1000} (Sec-
tion 4.5).
Training data is required for three procedures in R-CNN:
(1) CNN fine-tuning, (2) detector SVM training, and (3)
bounding-box regressor training. CNN fine-tuning was run
for 50k SGD iteration on val1+trainN using the exact same
settings as were used for PASCAL. Fine-tuning on a sin-
gle NVIDIA Tesla K20 took 13 hours using Caffe. For
SVM training, all ground-truth boxes from val 1+trainN
were used as positive examples for their respective classes.
Hard negative mining was performed on a randomly se-
lected subset of 5000 images from val 1. An initial experi-
ment indicated that mining negatives from all of val1, versus
a 5000 image subset (roughly half of it), resulted in only a
0.5 percentage point drop in mAP, while cutting SVM train-
ing time in half. No negative examples were taken from
2Relative imbalance is measured as|a− b|/(a + b) where a and b are
class counts in each half of the split.
train because the annotations are not exhaustive. The ex-
tra sets of verified negative images were not used. The
bounding-box regressors were trained on val1.
4.4. Validation and evaluation
Before submitting results to the evaluation server, we
validated data usage choices and the effect of fine-tuning
and bounding-box regression on the val2 set using the train-
ing data described above. All system hyperparameters (e.g.,
SVM C hyperparameters, padding used in region warp-
ing, NMS thresholds, bounding-box regression hyperpa-
rameters) were fixed at the same values used for PAS-
CAL. Undoubtedly some of these hyperparameter choices
are slightly suboptimal for ILSVRC, however the goal of
this work was to produce a preliminary R-CNN result on
ILSVRC without extensive dataset tuning. After selecting
the best choices on val 2, we submitted exactly two result
files to the ILSVRC2013 evaluation server. The first sub-
mission was without bounding-box regression and the sec-
ond submission was with bounding-box regression. For
these submissions, we expanded the SVM and bounding-
box regressor training sets to use val +train1k and val, re-
spectively. We used the CNN that was fine-tuned on
val1+train1k to avoid re-running fine-tuning and feature
computation.
4.5. Ablation study
Table 4 shows an ablation study of the effects of differ-
ent amounts of training data, fine-tuning, and bounding-
box regression. A first observation is that mAP on val 2
matches mAP on test very closely. This gives us confi-
dence that mAP on val 2 is a good indicator of test set per-
formance. The first result, 20.9%, is what R-CNN achieves
using a CNN pre-trained on the ILSVRC2012 classifica-
tion dataset (no fine-tuning) and given access to the small
amount of training data in val1 (recall that half of the classes
in val 1 have between 15 and 55 examples). Expanding
the training set to val 1+trainN improves performance to
24.1%, with essentially no difference between N = 500
andN = 1000. Fine-tuning the CNN using examples from
just val 1 gives a modest improvement to 26.5%, however
there is likely significant overfitting due to the small number
of positive training examples. Expanding the fine-tuning
set to val 1+train1k, which adds up to 1000 positive exam-
ples per class from the train set, helps significantly, boosting
mAP to 29.7%. Bounding-box regression improves results
to 31.0%, which is a smaller relative gain that what was ob-
served in PASCAL.
4.6. Relationship to OverFeat
There is an interesting relationship between R-CNN and
OverFeat: OverFeat can be seen (roughly) as a special case
of R-CNN. If one were to replace selective search region
9

test set val2 val2 val2 val2 val2 val2 test test
SVM training set val1 val1+train.5k val1+train1k val1+train1k val1+train1k val1+train1k val+train1k val+train1k
CNN fine-tuning set n/a n/a n/a val 1 val1+train1k val1+train1k val1+train1k val1+train1k
bbox reg set n/a n/a n/a n/a n/a val 1 n/a val
CNN feature layer fc6 fc6 fc6 fc7 fc7 fc7 fc7 fc7
mAP 20.9 24.1 24.1 26.5 29.7 31.0 30.2 31.4
median AP 17.7 21.0 21.4 24.8 29.2 29.6 29.0 30.3
Table 4: ILSVRC2013 ablation study of data usage choices, fine-tuning, and bounding-box regression.
proposals with a multi-scale pyramid of regular square re-
gions and change the per-class bounding-box regressors to
a single bounding-box regressor, then the systems would
be very similar (modulo some potentially significant differ-
ences in how they are trained: CNN detection fine-tuning,
using SVMs, etc.). It is worth noting that OverFeat has
a significant speed advantage over R-CNN: it is about 9x
faster, based on a figure of 2 seconds per image quoted from
[34]. This speed comes from the fact that OverFeat’s slid-
ing windows (i.e., region proposals) are not warped at the
image level and therefore computation can be easily shared
between overlapping windows. Sharing is implemented by
running the entire network in a convolutional fashion over
arbitrary-sized inputs. Speeding up R-CNN should be pos-
sible in a variety of ways and remains as future work.
5. Semantic segmentation
Region classification is a standard technique for seman-
tic segmentation, allowing us to easily apply R-CNN to the
PASCAL VOC segmentation challenge. To facilitate a di-
rect comparison with the current leading semantic segmen-
tation system (called O 2P for “second-order pooling”) [4],
we work within their open source framework. O 2P uses
CPMC to generate 150 region proposals per image and then
predicts the quality of each region, for each class, using
support vector regression (SVR). The high performance of
their approach is due to the quality of the CPMC regions
and the powerful second-order pooling of multiple feature
types (enriched variants of SIFT and LBP). We also note
that Farabet et al. [16] recently demonstrated good results
on several dense scene labeling datasets (not including PAS-
CAL) using a CNN as a multi-scale per-pixel classifier.
We follow [2, 4] and extend the PASCAL segmentation
training set to include the extra annotations made available
by Hariharan et al. [22]. Design decisions and hyperparam-
eters were cross-validated on the VOC 2011 validation set.
Final test results were evaluated only once.
CNN features for segmentation. We evaluate three strate-
gies for computing features on CPMC regions, all of which
begin by warping the rectangular window around the re-
gion to 227 × 227. The first strategy ( full) ignores the re-
gion’s shape and computes CNN features directly on the
warped window, exactly as we did for detection. However,
these features ignore the non-rectangular shape of the re-
gion. Two regions m

[... truncated for benchmark fixture size — see script body_max_chars ...]


## References

[1] B. Alexe, T. Deselaers, and V . Ferrari. Measuring the object-
ness of image windows. TPAMI, 2012. 2
[2] P. Arbel ́aez, B. Hariharan, C. Gu, S. Gupta, L. Bourdev, and
J. Malik. Semantic segmentation using regions and parts. In
CVPR, 2012. 10, 11
[3] P. Arbel ́aez, J. Pont-Tuset, J. Barron, F. Marques, and J. Ma-
lik. Multiscale combinatorial grouping. In CVPR, 2014. 3
[4] J. Carreira, R. Caseiro, J. Batista, and C. Sminchisescu. Se-
mantic segmentation with second-order pooling. In ECCV,
2012. 4, 10, 11, 13, 14
[5] J. Carreira and C. Sminchisescu. CPMC: Automatic ob-
ject segmentation using constrained parametric min-cuts.
TPAMI, 2012. 2, 3
[6] D. Cires ̧an, A. Giusti, L. Gambardella, and J. Schmidhu-
ber. Mitosis detection in breast cancer histology images with
deep neural networks. In MICCAI, 2013. 3
[7] N. Dalal and B. Triggs. Histograms of oriented gradients for
human detection. In CVPR, 2005. 1
[8] T. Dean, M. A. Ruzon, M. Segal, J. Shlens, S. Vijaya-
narasimhan, and J. Yagnik. Fast, accurate detection of
100,000 object classes on a single machine. In CVPR, 2013.
3
[9] J. Deng, A. Berg, S. Satheesh, H. Su, A. Khosla, and L. Fei-
Fei. ImageNet Large Scale Visual Recognition Competition
2012 (ILSVRC2012). http://www.image-net.org/
challenges/LSVRC/2012/. 1
[10] J. Deng, W. Dong, R. Socher, L.-J. Li, K. Li, and L. Fei-
Fei. ImageNet: A large-scale hierarchical image database.
In CVPR, 2009. 1
[11] J. Deng, O. Russakovsky, J. Krause, M. Bernstein, A. C.
Berg, and L. Fei-Fei. Scalable multi-label annotation. In
CHI, 2014. 8
[12] J. Donahue, Y . Jia, O. Vinyals, J. Hoffman, N. Zhang,
E. Tzeng, and T. Darrell. DeCAF: A Deep Convolutional
Activation Feature for Generic Visual Recognition. InICML,
2014. 2
[13] M. Douze, H. J ́egou, H. Sandhawalia, L. Amsaleg, and
C. Schmid. Evaluation of gist descriptors for web-scale im-
age search. In Proc. of the ACM International Conference on
Image and Video Retrieval, 2009. 13
[14] I. Endres and D. Hoiem. Category independent object pro-
posals. In ECCV, 2010. 3
[15] M. Everingham, L. Van Gool, C. K. I. Williams, J. Winn, and
A. Zisserman. The PASCAL Visual Object Classes (VOC)
Challenge. IJCV, 2010. 1, 4
[16] C. Farabet, C. Couprie, L. Najman, and Y . LeCun. Learning
hierarchical features for scene labeling. TPAMI, 2013. 10
[17] P. Felzenszwalb, R. Girshick, D. McAllester, and D. Ra-
manan. Object detection with discriminatively trained part
based models. TPAMI, 2010. 2, 4, 7, 12
[18] S. Fidler, R. Mottaghi, A. Yuille, and R. Urtasun. Bottom-up
segmentation for top-down detection. In CVPR, 2013. 4, 5
[19] K. Fukushima. Neocognitron: A self-organizing neu-
ral network model for a mechanism of pattern recogni-
tion unaffected by shift in position. Biological cybernetics,
36(4):193–202, 1980. 1
[20] R. Girshick, P. Felzenszwalb, and D. McAllester. Discrimi-
natively trained deformable part models, release 5. http:
//www.cs.berkeley.edu/ ̃rbg/latent-v5/. 2,
5, 6, 7
[21] C. Gu, J. J. Lim, P. Arbel ́aez, and J. Malik. Recognition
using regions. In CVPR, 2009. 2
[22] B. Hariharan, P. Arbel ́aez, L. Bourdev, S. Maji, and J. Malik.
Semantic contours from inverse detectors. In ICCV, 2011.
10
[23] D. Hoiem, Y . Chodpathumwan, and Q. Dai. Diagnosing error
in object detectors. In ECCV. 2012. 2, 7, 8
[24] Y . Jia. Caffe: An open source convolutional archi-
tecture for fast feature embedding. http://caffe.
berkeleyvision.org/, 2013. 3
[25] A. Krizhevsky, I. Sutskever, and G. Hinton. ImageNet clas-
sification with deep convolutional neural networks. InNIPS,
2012. 1, 3, 4, 7
[26] Y . LeCun, B. Boser, J. Denker, D. Henderson, R. Howard,
W. Hubbard, and L. Jackel. Backpropagation applied to
handwritten zip code recognition. Neural Comp., 1989. 1
[27] Y . LeCun, L. Bottou, Y . Bengio, and P. Haffner. Gradient-
based learning applied to document recognition. Proc. of the
IEEE, 1998. 1
[28] J. J. Lim, C. L. Zitnick, and P. Doll ́ar. Sketch tokens: A
learned mid-level representation for contour and object de-
tection. In CVPR, 2013. 6, 7
14

class AP class AP class AP class AP class AP
accordion 50.8 centipede 30.4 hair spray 13.8 pencil box 11.4 snowplow 69.2
airplane 50.0 chain saw 14.1 hamburger 34.2 pencil sharpener 9.0 soap dispenser 16.8
ant 31.8 chair 19.5 hammer 9.9 perfume 32.8 soccer ball 43.7
antelope 53.8 chime 24.6 hamster 46.0 person 41.7 sofa 16.3
apple 30.9 cocktail shaker 46.2 harmonica 12.6 piano 20.5 spatula 6.8
armadillo 54.0 coffee maker 21.5 harp 50.4 pineapple 22.6 squirrel 31.3
artichoke 45.0 computer keyboard 39.6 hat with a wide brim 40.5 ping-pong ball 21.0 starfish 45.1
axe 11.8 computer mouse 21.2 head cabbage 17.4 pitcher 19.2 stethoscope 18.3
baby bed 42.0 corkscrew 24.2 helmet 33.4 pizza 43.7 stove 8.1
backpack 2.8 cream 29.9 hippopotamus 38.0 plastic bag 6.4 strainer 9.9
bagel 37.5 croquet ball 30.0 horizontal bar 7.0 plate rack 15.2 strawberry 26.8
balance beam 32.6 crutch 23.7 horse 41.7 pomegranate 32.0 stretcher 13.2
banana 21.9 cucumber 22.8 hotdog 28.7 popsicle 21.2 sunglasses 18.8
band aid 17.4 cup or mug 34.0 iPod 59.2 porcupine 37.2 swimming trunks 9.1
banjo 55.3 diaper 10.1 isopod 19.5 power drill 7.9 swine 45.3
baseball 41.8 digital clock 18.5 jellyfish 23.7 pretzel 24.8 syringe 5.7
basketball 65.3 dishwasher 19.9 koala bear 44.3 printer 21.3 table 21.7
bathing cap 37.2 dog 76.8 ladle 3.0 puck 14.1 tape player 21.4
beaker 11.3 domestic cat 44.1 ladybug 58.4 punching bag 29.4 tennis ball 59.1
bear 62.7 dragonfly 27.8 lamp 9.1 purse 8.0 tick 42.6
bee 52.9 drum 19.9 laptop 35.4 rabbit 71.0 tie 24.6
bell pepper 38.8 dumbbell 14.1 lemon 33.3 racket 16.2 tiger 61.8
bench 12.7 electric fan 35.0 lion 51.3 ray 41.1 toaster 29.2
bicycle 41.1 elephant 56.4 lipstick 23.1 red panda 61.1 traffic light 24.7
binder 6.2 face powder 22.1 lizard 38.9 refrigerator 14.0 train 60.8
bird 70.9 fig 44.5 lobster 32.4 remote control 41.6 trombone 13.8
bookshelf 19.3 filing cabinet 20.6 maillot 31.0 rubber eraser 2.5 trumpet 14.4
bow tie 38.8 flower pot 20.2 maraca 30.1 rugby ball 34.5 turtle 59.1
bow 9.0 flute 4.9 microphone 4.0 ruler 11.5 tv or monitor 41.7
bowl 26.7 fox 59.3 microwave 40.1 salt or pepper shaker 24.6 unicycle 27.2
brassiere 31.2 french horn 24.2 milk can 33.3 saxophone 40.8 vacuum 19.5
burrito 25.7 frog 64.1 miniskirt 14.9 scorpion 57.3 violin 13.7
bus 57.5 frying pan 21.5 monkey 49.6 screwdriver 10.6 volleyball 59.7
butterfly 88.5 giant panda 42.5 motorcycle 42.2 seal 20.9 waffle iron 24.0
camel 37.6 goldfish 28.6 mushroom 31.8 sheep 48.9 washer 39.8
can opener 28.9 golf ball 51.3 nail 4.5 ski 9.0 water bottle 8.1
car 44.5 golfcart 47.9 neck brace 31.6 skunk 57.9 watercraft 40.9
cart 48.0 guacamole 32.3 oboe 27.5 snail 36.2 whale 48.6
cattle 32.3 guitar 33.1 orange 38.8 snake 33.8 wine bottle 31.2
cello 28.9 hair dryer 13.0 otter 22.2 snowmobile 58.8 zebra 49.6
Table 8: Per-class average precision (%) on the ILSVRC2013 detection test set.
[29] D. Lowe. Distinctive image features from scale-invariant
keypoints. IJCV, 2004. 1
[30] A. Oliva and A. Torralba. Modeling the shape of the scene:
A holistic representation of the spatial envelope.IJCV, 2001.
13
[31] X. Ren and D. Ramanan. Histograms of sparse codes for
15

lemon 0.79
lemon 0.70
lemon 0.56lemon 0.50
person 0.88
person 0.72
cocktail shaker 0.56
dog 0.97dog 0.85 dog 0.57
bird 0.63
dog 0.97dog 0.95
dog 0.64
helmet 0.65
helmet 0.52
motorcycle 0.65
person 0.75
person 0.58
snowmobile 0.83
snowmobile 0.83
bow tie 0.86
person 0.82
bird 0.61
dog 0.66
dog 0.61
domestic cat 0.57
bird 0.96
dog 0.91
dog 0.77
sofa 0.71
dog 0.95
dog 0.55
ladybug 1.00
person 0.87
car 0.96 car 0.66car 0.63
bird 0.98
person 0.65
watercraft 1.00
watercraft 0.69
pretzel 0.78
car 0.96
person 0.65person 0.58person 0.52
person 0.52
bird 0.99 bird 0.91
bird 0.75
dog 0.98
flower pot 0.62
dog 0.97dog 0.56
train 1.00
train 0.53
armadillo 1.00
armadillo 0.56
bird 0.93
dog 0.92
swine 0.88
bird 1.00
butterfly 0.96
person 0.90
flower pot 0.62
snake 0.70
turtle 0.54
bell pepper 0.81
bell pepper 0.62
bell pepper 0.54
ruler 1.00
antelope 0.53
mushroom 0.93
tv or monitor 0.82
tv or monitor 0.76tv or monitor 0.54
bird 0.89
lipstick 0.80
lipstick 0.61
person 0.58
dog 0.97
soccer ball 0.90
Figure 8: Example detections on the val2 set from the configuration that achieved 31.0% mAP on val2. Each image was sampled randomly
(these are not curated). All detections at precision greater than 0.5 are shown. Each detection is labeled with the predicted class and the
precision value of that detection from the detector’s precision-recall curve. Viewing digitally with zoom is recommended.
16

baby bed 0.55helmet 0.51
pitcher 0.57
dog 0.98
hat with a wide brim 0.78
person 0.86
bird 0.52table 0.60
monkey 0.97
table 0.68
watercraft 0.55
person 0.88
car 0.61
person 0.87
person 0.51
sunglasses 0.51
dog 0.94dog 0.55
bird 0.52
monkey 0.87
monkey 0.81
swine 0.50
dog 0.97
hat with a wide brim 0.96
snake 0.74
dog 0.93
person 0.77
dog 0.97
guacamole 0.64
pretzel 0.69
table 0.54
dog 0.71
person 0.85
ladybug 0.90
person 0.52
zebra 0.83 zebra 0.80
zebra 0.55
zebra 0.52
dog 0.98
hat with a wide brim 0.60person 0.85
person 0.81 person 0.73
elephant 1.00
bird 0.99
person 0.58
dog 0.98
cart 1.00
chair 0.79chair 0.64
person 0.91person 0.87 person 0.57
person 0.52
computer keyboard 0.52
dog 0.97 dog 0.92
person 0.77
bird 0.94
butterfly 0.98
person 0.73
person 0.61
bird 1.00
bird 0.78
person 0.91 person 0.75
stethoscope 0.83
bird 0.83
Figure 9: More randomly selected examples. See Figure 8 caption for details. Viewing digitally with zoom is recommended.
17

person 0.81
person 0.57
person 0.53
motorcycle 0.64
person 0.73
person 0.51
bagel 0.57
pineapple 1.00
bowl 0.63
guacamole 1.00tennis ball 0.60
lemon 0.88
lemon 0.86lemon 0.80
lemon 0.78
orange 0.78
orange 0.73
orange 0.71
golf ball 1.00
golf ball 1.00
golf ball 0.89
golf ball 0.81
golf ball 0.79
golf ball 0.76golf ball 0.60
golf ball 0.60
golf ball 0.51
lemon 0.53
soccer ball 0.67
lamp 0.61
table 0.59
bee 0.85
jellyfish 0.71
bowl 0.54
hamburger 0.78
dumbbell 1.00person 0.52
microphone 1.00
person 0.85
head cabbage 0.83
head cabbage 0.75
dog 0.74
goldfish 0.76
person 0.57
guitar 1.00
guitar 1.00
guitar 0.88
table 0.63
computer keyboard 0.78
microwave 0.60
table 0.53
tick 0.64
lemon 0.80
tennis ball 0.67
rabbit 1.00
dog 0.98
person 0.81
person 0.92
sunglasses 0.52
watercraft 0.86
milk can 1.00
milk can 1.00
bookshelf 0.50
chair 0.86
giant panda 0.61
person 0.87
antelope 0.74
cattle 0.81
dog 0.87
horse 0.78
pomegranate 1.00
chair 0.86
tv or monitor 0.52
antelope 0.68
bird 0.94
snake 0.60
dog 0.98
dog 0.88
person 0.79
snake 0.76
table 0.62
tv or monitor 0.80
tv or monitor 0.58
tv or monitor 0.54
lamp 0.86lamp 0.65
table 0.83
monkey 1.00monkey 1.00
monkey 0.90
monkey 0.88
monkey 0.52
dog 0.88fox 1.00
fox 0.81
person 0.88
watercraft 0.91
watercraft 0.56
bird 0.95
bird 0.78
isopod 0.56
bird 0.69
starfish 0.67
dragonfly 0.70
dragonfly 0.60
hamburger 0.72
hamburger 0.60
cup or mug 0.72
electric fan 1.00
electric fan 0.83
electric fan 0.78helmet 0.64
soccer ball 0.63
Figure 10: Curated examples. Each image was selected because we found it impressive, surprising, interesting, or amusing. Viewing
digitally with zoom is recommended.
18

object detection. In CVPR, 2013. 6, 7
[32] H. A. Rowley, S. Baluja, and T. Kanade. Neural network-
based face detection. TPAMI, 1998. 2
[33] D. E. Rumelhart, G. E. Hinton, and R. J. Williams. Learn-
ing internal representations by error propagation. Parallel
Distributed Processing, 1:318–362, 1986. 1
[34] P. Sermanet, D. Eigen, X. Zhang, M. Mathieu, R. Fergus,
and Y . LeCun. OverFeat: Integrated Recognition, Localiza-
tion and Detection using Convolutional Networks. In ICLR,
2014. 1, 2, 4, 10
[35] P. Sermanet, K. Kavukcuoglu, S. Chintala, and Y . LeCun.
Pedestrian detection with unsupervised multi-stage feature
learning. In CVPR, 2013. 2
[36] H. Su, J. Deng, and L. Fei-Fei. Crowdsourcing annotations
for visual object detection. In AAAI Technical Report, 4th
Human Computation Workshop, 2012. 8
[37] K. Sung and T. Poggio. Example-based learning for view-
based human face detection. Technical Report A.I. Memo
No. 1521, Massachussets Institute of Technology, 1994. 4
[38] C. Szegedy, A. Toshev, and D. Erhan. Deep neural networks
for object detection. In NIPS, 2013. 2
[39] J. Uijlings, K. van de Sande, T. Gevers, and A. Smeulders.
Selective search for object recognition. IJCV, 2013. 1, 2, 3,
4, 5, 9
[40] R. Vaillant, C. Monrocq, and Y . LeCun. Original approach
for the localisation of objects in images. IEE Proc on Vision,
Image, and Signal Processing, 1994. 2
[41] X. Wang, M. Yang, S. Zhu, and Y . Lin. Regionlets for generic
object detection. In ICCV, 2013. 3, 5
[42] M. Zeiler, G. Taylor, and R. Fergus. Adaptive deconvolu-
tional networks for mid and high level feature learning. In
CVPR, 2011. 4
[43] K. Simonyan and A. Zisserman. Very Deep Convolu-
tional Networks for Large-Scale Image Recognition. arXiv
preprint, arXiv:1409.1556, 2014. 6, 7, 14
19

person 0.82
snake 0.76
frog 0.78
bird 0.79
goldfish 0.76
goldfish 0.76
goldfish 0.58
person 0.94
stethoscope 0.56
person 0.95person 0.92person 0.67
person 0.60
table 0.81
jellyfish 0.67
lemon 0.52
person 0.78
person 0.65
watercraft 0.55
baseball 1.00
person 0.94
person 0.82
person 0.80
person 0.61
person 0.55
person 0.52
computer keyboard 0.81
dog 0.60 person 0.88
person 0.79
person 0.68
person 0.59
tv or monitor 0.82
lizard 0.58
chair 0.50
person 0.74
table 0.82
person 0.94
person 0.94
person 0.95
person 0.81person 0.69
rugby ball 0.91
person 0.84 person 0.59
volleyball 0.70
pineapple 1.00
brassiere 0.71
person 0.95 person 0.94person 0.94
person 0.81 person 0.80person 0.80
person 0.79
person 0.79
person 0.69
person 0.66
person 0.58
person 0.56person 0.54
swimming trunks 0.56
baseball 0.86
helmet 0.74
person 0.75
miniskirt 0.64
person 0.92
vacuum 1.00
dog 0.98
dog 0.93
person 0.94 person 0.75
person 0.65
person 0.53
ski 0.80 ski 0.80
bird 0.55
tiger 1.00
tiger 0.67
tiger 0.59
bird 0.56
whale 1.00
chair 0.53
person 0.92
person 0.92
person 0.82person 0.78
bowl 0.52
strawberry 0.79strawberry 0.70
burrito 0.54
croquet ball 0.91croquet ball 0.91croquet ball 0.91 croquet ball 0.91
mushroom 0.57
watercraft 0.91
watercraft 0.87
watercraft 0.58
plastic bag 0.62
plastic bag 0.62
whale 0.88
car 0.70
dog 0.94
tv or monitor 0.57
cart 0.80
person 0.79
person 0.53
hat with a wide brim 0.89person 0.88
person 0.82
person 0.79
person 0.56
person 0.54
traffic light 0.79
bird 0.59
cucumber 0.53
cucumber 0.52
antelope 1.00
antelope 1.00
antelope 0.94
antelope 0.73
antelope 0.63
antelope 0.63
fox 0.57
balance beam 0.50horizontal bar 1.00
person 0.80
person 0.90
snake 0.64
dog 0.98
dog 0.97
helmet 0.69
horse 0.92
horse 0.69
person 0.82
person 0.72
orange 0.79
orange 0.71
orange 0.66
orange 0.66
orange 0.59
orange 0.56
bird 0.97
bird 0.96
bird 0.96
bird 0.94
bird 0.89
bird 0.64
bird 0.56
bird 0.53bird 0.52
guitar 1.00
person 0.82
bicycle 0.92
person 0.90
person 0.83
car 1.00 car 0.97
dog 0.98dog 0.86
dog 0.85
dog 0.65dog 0.50
person 0.83
person 0.80
person 0.74person 0.54
elephant 0.60
Figure 11: More curated examples. See Figure 10 caption for details. Viewing digitally with zoom is recommended.
20

pool5 feature: (3,3,1) (top 1 − 24)
1.0 0.9 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,2) (top 1 − 24)
1.0 0.9 0.9 0.9 0.9 0.8 0.8 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,3) (top 1 − 24)
0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,4) (top 1 − 24)
0.9 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,5) (top 1 − 24)
0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,6) (top 1 − 24)
0.9 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,7) (top 1 − 24)
0.9 0.8 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6 0.6 0.6
pool5 feature: (3,3,8) (top 1 − 24)
0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,9) (top 1 − 24)
0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,10) (top 1 − 24)
0.9 0.8 0.8 0.7 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.5 0.5
pool5 feature: (3,3,11) (top 1 − 24)
0.7 0.7 0.7 0.7 0.7 0.6 0.6 0.6 0.6 0.6 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,12) (top 1 − 24)
0.9 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,13) (top 1 − 24)
0.9 0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8
0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8
pool5 feature: (3,3,14) (top 1 − 24)
0.9 0.9 0.9 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8
0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,15) (top 1 − 24)
0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8 0.8
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,16) (top 1 − 24)
0.9 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,17) (top 1 − 24)
0.9 0.9 0.8 0.8 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7
0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7
pool5 feature: (3,3,18) (top 1 − 24)
0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,19) (top 1 − 24)
0.9 0.8 0.8 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
pool5 feature: (3,3,20) (top 1 − 24)
1.0 0.9 0.7 0.7 0.7 0.7 0.7 0.7 0.6 0.6 0.6 0.6
0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.6
Figure 12: We show the 24 region proposals, out of the approximately 10 million regions in VOC 2007 test, that most strongly
activate each of 20 units. Each montage is labeled by the unit’s (y, x, channel) position in the6× 6× 256 dimensional pool5 feature map.
Each image region is drawn with an overlay of the unit’s receptive field in white. The activation value (which we normalize by dividing by
the max activation value over all units in a channel) is shown in the receptive field’s upper-left corner. Best viewed digitally with zoom.
21