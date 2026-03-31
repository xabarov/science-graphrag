# Selective Search for Object Recognition

J.R.R. Uijlings∗1,2, K.E.A. van de Sande †2, T. Gevers2, and A.W.M. Smeulders2
1University of Trento, Italy
2University of Amsterdam, the Netherlands
Technical Report 2012, submitted to IJCV

## Abstract

This paper addresses the problem of generating possible obj ect lo-
cations for use in object recognition. We introduce Selective Search
which combines the strength of both an exhaustive search and seg-
mentation. Like segmentation, we use the image structure to guide
our sampling process. Like exhaustive search, we aim to capt ure
all possible object locations. Instead of a single techniqu e to gen-
erate possible object locations, we diversify our search and use a
variety of complementary image partitionings to deal with a s many
image conditions as possible. Our Selective Search results in a
small set of data-driven, class-independent, high quality locations,
yielding 99% recall and a Mean Average Best Overlap of 0.879 a t
10,097 locations. The reduced number of locations compared to
an exhaustive search enables the use of stronger machine lea rning
techniques and stronger appearance models for object recog nition.
In this paper we show that our selective search enables the us e of
the powerful Bag-of-Words model for recognition. The Selec tive
Search software is made publicly available 1.

## Body

1 Introduction
For a long time, objects were sought to be delineated before t heir
identification. This gave rise to segmentation, which aims f or
a unique partitioning of the image through a generic algorit hm,
where there is one part for all object silhouettes in the imag e. Re-
search on this topic has yielded tremendous progress over th e past
years [3, 6, 13, 26]. But images are intrinsically hierarchi cal: In
Figure 1a the salad and spoons are inside the salad bowl, whic h in
turn stands on the table. Furthermore, depending on the cont ext the
term table in this picture can refer to only the wood or include ev-
erything on the table. Therefore both the nature of images an d the
different uses of an object category are hierarchical. This prohibits
the unique partitioning of objects for all but the most speci fic pur-
poses. Hence for most tasks multiple scales in a segmentatio n are a
necessity. This is most naturally addressed by using a hiera rchical
partitioning, as done for example by Arbelaez et al. [3].
Besides that a segmentation should be hierarchical, a gener ic so-
lution for segmentation using a single strategy may not exis t at all.
There are many conflicting reasons why a region should be grouped
together: In Figure 1b the cats can be separated using colour , but
their texture is the same. Conversely, in Figure 1c the chame leon
∗jrr@disi.unitn.it
†ksande@uva.nl
1http://disi.unitn.it/ ̃uijlings/SelectiveSearch.html
(a)
 (b)
(c)
 (d)
Figure 1: There is a high variety of reasons that an image regi on
forms an object. In (b) the cats can be distinguished by colou r, not
texture. In (c) the chameleon can be distinguished from the s ur-
rounding leaves by texture, not colour. In (d) the wheels can be part
of the car because they are enclosed, not because they are sim ilar
in texture or colour. Therefore, to find objects in a structur ed way
it is necessary to use a variety of diverse strategies. Furth ermore,
an image is intrinsically hierarchical as there is no single scale for
which the complete table, salad bowl, and salad spoon can be found
in (a).
is similar to its surrounding leaves in terms of colour, yet i ts tex-
ture differs. Finally, in Figure 1d, the wheels are wildly di fferent
from the car in terms of both colour and texture, yet are enclo sed
by the car. Individual visual features therefore cannot res olve the
ambiguity of segmentation.
And, finally, there is a more fundamental problem. Regions wi th
very different characteristics, such as a face over a sweate r, can
only be combined into one object after it has been establishe d that
the object at hand is a human. Hence without prior recognitio n it is
hard to decide that a face and a sweater are part of one object [ 29].
This has led to the opposite of the traditional approach: to d o
localisation through the identification of an object. This r ecent ap-
proach in object recognition has made enormous progress in l ess
than a decade [8, 12, 16, 35]. With an appearance model learne d
from examples, an exhaustive search is performed where ever y lo-
cation within the image is examined as to not miss any potenti al
object location [8, 12, 16, 35].
1

However, the exhaustive search itself has several drawback s.
Searching every possible location is computationally infe asible.
The search space has to be reduced by using a regular grid, fixe d
scales, and fixed aspect ratios. In most cases the number of lo -
cations to visit remains huge, so much that alternative rest rictions
need to be imposed. The classifier is simplified and the appear ance
model needs to be fast. Furthermore, a uniform sampling yiel ds
many boxes for which it is immediately clear that they are not sup-
portive of an object. Rather then sampling locations blindl y using
an exhaustive search, a key question is: Can we steer the samp ling
by a data-driven analysis?
In this paper, we aim to combine the best of the intuitions of s eg-
mentation and exhaustive search and propose a data-driven selec-
tive search. Inspired by bottom-up segmentation, we aim to exploit
the structure of the image to generate object locations. Ins pired by
exhaustive search, we aim to capture all possible object loc ations.
Therefore, instead of using a single sampling technique, we aim
to diversify the sampling techniques to account for as many image
conditions as possible. Specifically, we use a data-driven grouping-
based strategy where we increase diversity by using a variet y of
complementary grouping criteria and a variety of complemen tary
colour spaces with different invariance properties. The se t of lo-
cations is obtained by combining the locations of these comp le-
mentary partitionings. Our goal is to generate a class-inde pendent,
data-driven, selective search strategy that generates a sm all set of
high-quality object locations.
Our application domain of selective search is object recogn ition.
We therefore evaluate on the most commonly used dataset for t his
purpose, the Pascal VOC detection challenge which consists of 20
object classes. The size of this dataset yields computation al con-
straints for our selective search. Furthermore, the use of this dataset
means that the quality of locations is mainly evaluated in te rms of
bounding boxes. However, our selective search applies to re gions
as well and is also applicable to concepts such as “grass”.
In this paper we propose selective search for object recogni tion.
Our main research questions are: (1) What are good diversifica tion
strategies for adapting segmentation as a selective search strategy?
(2) How effective is selective search in creating a small set of high-
quality locations within an image? (3) Can we use selective s earch
to employ more powerful classifiers and appearance models for ob-
ject recognition?
2 Related Work
We confine the related work to the domain of object recognitio n
and divide it into three categories: Exhaustive search, seg menta-
tion, and other sampling strategies that do not fall in eithe r cate-
gory.
2.1 Exhaustive Search
As an object can be located at any position and scale in the ima ge,
it is natural to search everywhere [8, 16, 36]. However, the v isual
search space is huge, making an exhaustive search computationally
expensive. This imposes constraints on the evaluation cost per lo-
cation and/or the number of locations considered. Hence mos t of
these sliding window techniques use a coarse search grid and fixed
aspect ratios, using weak classifiers and economic image fea tures
such as HOG [8, 16, 36]. This method is often used as a preselec -
tion step in a cascade of classifiers [16, 36].
Related to the sliding window technique is the highly succes sful
part-based object localisation method of Felzenszwalb et al . [12].
Their method also performs an exhaustive search using a line ar
SVM and HOG features. However, they search for objects and
object parts, whose combination results in an impressive ob ject de-
tection performance.
Lampert et al . [17] proposed using the appearance model to
guide the search. This both alleviates the constraints of us ing a
regular grid, fixed scales, and fixed aspect ratio, while at th e same
time reduces the number of locations visited. This is done by di-
rectly searching for the optimal window within the image usi ng a
branch and bound technique. While they obtain impressive res ults
for linear classifiers, [1] found that for non-linear classi fiers the
method in practice still visits over a 100,000 windows per im age.
Instead of a blind exhaustive search or a branch and bound
search, we propose selective search. We use the underlying i m-
age structure to generate object locations. In contrast to t he dis-
cussed methods, this yields a completely class-independen t set of
locations. Furthermore, because we do not use a fixed aspect r a-
tio, our method is not limited to objects but should be able to find
stuff like “grass” and “sand” as well (this also holds for [17 ]). Fi-
nally, we hope to generate fewer locations, which should mak e the
problem easier as the variability of samples becomes lower. And
more importantly, it frees up computational power which can be
used for stronger machine learning techniques and more powe rful
appearance models.
2.2 Segmentation
Both Carreira and Sminchisescu [4] and Endres and Hoiem [9] pro-
pose to generate a set of class independent object hypothese s using
segmentation. Both methods generate multiple foreground/ back-
ground segmentations, learn to predict the likelihood that a fore-
ground segment is a complete object, and use this to rank the s eg-
ments. Both algorithms show a promising ability to accurate ly
delineate objects within images, confirmed by [19] who achie ve
state-of-the-art results on pixel-wise image classificati on using [4].
As common in segmentation, both methods rely on a single stro ng
algorithm for identifying good regions. They obtain a varie ty of
locations by using many randomly initialised foreground and back-
ground seeds. In contrast, we explicitly deal with a variety of image
conditions by using different grouping criteria and differ ent repre-
sentations. This means a lower computational investment as we do
not have to invest in the single best segmentation strategy, such as
using the excellent yet expensive contour detector of [3]. F urther-
more, as we deal with different image conditions separately , we
expect our locations to have a more consistent quality. Fina lly, our
selective search paradigm dictates that the most interesti ng ques-
tion is not how our regions compare to [4, 9], but rather how they
can complement each other.
Gu et al. [15] address the problem of carefully segmenting and
recognizing objects based on their parts. They first generat e a set
of part hypotheses using a grouping method based on Arbelaez et
al. [3]. Each part hypothesis is described by both appearance a nd
shape features. Then, an object is recognized and carefully delin-
eated by using its parts, achieving good results for shape re cogni-
tion. In their work, the segmentation is hierarchical and yi elds seg-
ments at all scales. However, they use a single grouping stra tegy
2

Figure 2: Two examples of our selective search showing the ne cessity of different scales. On the left we find many objects a t different
scales. On the right we necessarily find the objects at differ ent scales as the girl is contained by the tv.
whose power of discovering parts or objects is left unevalua ted. In
this work, we use multiple complementary strategies to deal with
as many image conditions as possible. We include the locatio ns
generated using [3] in our evaluation.
2.3 Other Sampling Strategies
Alexe et al . [2] address the problem of the large sampling space
of an exhaustive search by proposing to search for any object, in-
dependent of its class. In their method they train a classifie r on the
object windows of those objects which have a well-defined sha pe
(as opposed to stuff like “grass” and “sand”). Then instead o f a full
exhaustive search they randomly sample boxes to which they apply
their classifier. The boxes with the highest “objectness” me asure
serve as a set of object hypotheses. This set is then used to gr eatly
reduce the number of windows evaluated by class-specific obj ect
detectors. We compare our method with their work.
Another strategy is to use visual words of the Bag-of-Words
model to predict the object location. V edaldiet al. [34] use jumping
windows [5], in which the relation between individual visual words
and the object location is learned to predict the object loca tion in
new images. Maji and Malik [23] combine multiple of these rel a-
tions to predict the object location using a Hough-transfor m, after
which they randomly sample windows close to the Hough maxi-
mum. In contrast to learning, we use the image structure to sa mple
a set of class-independent object hypotheses.
To summarize, our novelty is as follows. Instead of an exhaus -
tive search [8, 12, 16, 36] we use segmentation as selective s earch
yielding a small set of class independent object locations. In con-
trast to the segmentation of [4, 9], instead of focusing on th e best
segmentation algorithm [3], we use a variety of strategies t o deal
with as many image conditions as possible, thereby severely reduc-
ing computational costs while potentially capturing more o bjects
accurately. Instead of learning an objectness measure on ra ndomly
sampled boxes [2], we use a bottom-up grouping procedure to g en-
erate good object locations.
3 Selective Search
In this section we detail our selective search algorithm for object
recognition and present a variety of diversification strategies to deal
with as many image conditions as possible. A selective searc h al-
gorithm is subject to the following design considerations:
Capture All Scales. Objects can occur at any scale within the im-
age. Furthermore, some objects have less clear boundaries
then other objects. Therefore, in selective search all obje ct
scales have to be taken into account, as illustrated in Figur e
2. This is most naturally achieved by using an hierarchical
algorithm.
Diversification. There is no single optimal strategy to group re-
gions together. As observed earlier in Figure 1, regions may
form an object because of only colour, only texture, or because
parts are enclosed. Furthermore, lighting conditions such as
shading and the colour of the light may influence how regions
form an object. Therefore instead of a single strategy which
works well in most cases, we want to have a diverse set of
strategies to deal with all cases.
Fast to Compute. The goal of selective search is to yield a set of
possible object locations for use in a practical object reco gni-
tion framework. The creation of this set should not become a
computational bottleneck, hence our algorithm should be re a-
sonably fast.
3.1 Selective Search by Hierarchical Grouping
We take a hierarchical grouping algorithm to form the basis o f our
selective search. Bottom-up grouping is a popular approach to seg-
mentation [6, 13], hence we adapt it for selective search. Be cause
the process of grouping itself is hierarchical, we can natur ally gen-
erate locations at all scales by continuing the grouping process until
the whole image becomes a single region. This satisfies the co ndi-
tion of capturing all scales.
As regions can yield richer information than pixels, we want to
use region-based features whenever possible. To get a set of small
starting regions which ideally do not span multiple objects , we use
3

the fast method of Felzenszwalb and Huttenlocher [13], whic h [3]
found well-suited for such purpose.
Our grouping procedure now works as follows. We first use [13]
to create initial regions. Then we use a greedy algorithm to i ter-
atively group regions together: First the similarities bet ween all
neighbouring regions are calculated. The two most similar r egions
are grouped together, and new similarities are calculated b etween
the resulting region and its neighbours. The process of grou ping
the most similar regions is repeated until the whole image be comes
a single region. The general method is detailed in Algorithm 1.
Algorithm 1: Hierarchical Grouping Algorithm
Input: (colour) image
Output: Set of object location hypotheses L
Obtain initial regions R = {r1, · · ·, rn} using [13]
Initialise similarity set S = / 0
foreach Neighbouring region pair (ri, r j) do
Calculate similarity s(ri, r j)
S = S ∪ s(ri, r j)
while S ̸= / 0do
Get highest similarity s(ri, r j) = max(S)
Merge corresponding regions rt = ri ∪ r j
Remove similarities regarding ri : S = S \s(ri, r∗)
Remove similarities regarding r j : S = S \s(r∗, r j)
Calculate similarity set St between rt and its neighbours
S = S ∪ St
R = R ∪ rt
Extract object location boxes L from all regions in R
For the similarity s(ri, r j) between region ri and r j we want a va-
riety of complementary measures under the constraint that t hey are
fast to compute. In effect, this means that the similarities should be
based on features that can be propagated through the hierarc hy, i.e.
when merging region ri and r j into rt, the features of region rt need
to be calculated from the features of ri and r j without accessing the
image pixels.
3.2 Diversification Strategies
The second design criterion for selective search is to diver sify the
sampling and create a set of complementary strategies whose loca-
tions are combined afterwards. We diversify our selective s earch
(1) by using a variety of colour spaces with different invari ance
properties, (2) by using different similarity measures si j, and (3)
by varying our starting regions.
Complementary Colour Spaces. We want to account for dif-
ferent scene and lighting conditions. Therefore we perform our
hierarchical grouping algorithm in a variety of colour spac es with
a range of invariance properties. Specifically, we the follo wing
colour spaces with an increasing degree of invariance: (1) RGB,
(2) the intensity (grey-scale image) I, (3) Lab, (4) the rg chan-
nels of normalized RGB plus intensity denoted as rgI, (5) HSV , (6)
normalized RGB denoted as rgb, (7) C [14] which is an opponent
colour space where intensity is divided out, and finally (8) t he Hue
channel H from HSV . The specific invariance properties are listed
in Table 1.
Of course, for images that are black and white a change of colour
space has little impact on the final outcome of the algorithm. For
colour channels R G B I V L a b S r g C H
Light Intensity - - - - - - +/- +/- + + + + +
Shadows/shading - - - - - - +/- +/- + + + + +
Highlights - - - - - - - - - - - +/- +
colour spaces RGB I Lab rgI HSV rgb C H
Light Intensity - - +/- 2/3 2/3 + + +
Shadows/shading - - +/- 2/3 2/3 + + +
Highlights - - - - 1/3 - +/- +
Table 1: The invariance properties of both the individual co lour
channels and the colour spaces used in this paper, sorted by d e-
gree of invariance. A “+/-” means partial invariance. A frac tion
1/3 means that one of the three colour channels is invariant to sa id
property.
these images we rely on the other diversification methods for en-
suring good object locations.
In this paper we always use a single colour space throughout
the algorithm, meaning that both the initial grouping algor ithm of
[13] and our subsequent grouping algorithm are performed in this
colour space.
Complementary Similarity Measures. We define four comple-
mentary, fast-to-compute similarity measures. These meas ures are
all in range [0, 1] which facilitates combinations of these measures.
scolour(ri, r j) measures colour similarity. Specifically, for each re-
gion we obtain one-dimensional colour histograms for each
colour channel using 25 bins, which we found to work well.
This leads to a colour histogram Ci = {c1
i , · · ·, cn
i } for each
region ri with dimensionality n = 75 when three colour chan-
nels are used. The colour histograms are normalised using th e
L1 norm. Similarity is measured using the histogram intersec-
tion:
scolour(ri, r j) =
n
∑
k=1
min(ck
i , ck
j). (1)
The colour histograms can be efficiently propagated through
the hierarchy by
Ct = size(ri) × Ci + size(r j) × C j
size(ri) +size(rj) . (2)
The size of a resulting region is simply the sum of its con-
stituents: size (rt) = size(ri) +size(r j).
stexture(ri, r j) measures texture similarity. We represent texture us-
ing fast SIFT-like measurements as SIFT itself works well fo r
material recognition [20]. We take Gaussian derivatives in
eight orientations using
σ = 1 for each colour channel. For
each orientation for each colour channel we extract a his-
togram using a bin size of 10. This leads to a texture his-
togram Ti = {t1
i , · · ·,tn
i } for each region ri with dimension-
ality n = 240 when three colour channels are used. Texture
histograms are normalised using the L1 norm. Similarity is
measured using histogram intersection:
stexture(ri, r j) =
n
∑
k=1
min(tk
i ,tk
j ). (3)
Texture histograms are efficiently propagated through the h i-
erarchy in the same way as the colour histograms.
4

ssize(ri, r j) encourages small regions to merge early. This forces
regions in S, i.e. regions which have not yet been merged, to
be of similar sizes throughout the algorithm. This is desir-
able because it ensures that object locations at all scales a re
created at all parts of the image. For example, it prevents a
single region from gobbling up all other regions one by one,
yielding all scales only at the location of this growing regi on
and nowhere else. ssize(ri, r j) is defined as the fraction of the
image that ri and r j jointly occupy:
ssize(ri, r j) = 1 − size(ri) +size(rj)
size(im) , (4)
where size(im) denotes the size of the image in pixels.
sfill(ri, r j) measures how well region ri and r j fit into each other.
The idea is to fill gaps: if ri is contained in r j it is logical to
merge these first in order to avoid any holes. On the other
hand, if ri and r j are hardly touching each other they will
likely form a strange region and should not be merged. To
keep the measure fast, we use only the size of the regions and
of the containing boxes. Specifically, we define BBi j to be the
tight bounding box around ri and r j. Now sfill(ri, r j) is the
fraction of the image contained in BBi j which is not covered
by the regions of ri and r j:
fill(ri, r j) = 1 − size(BBi j) − size(ri) − size(ri)
size(im) (5)
We divide by size (im) for consistency with Equation 4. Note
that this measure can be efficiently calculated by keeping track
of the bounding boxes around each region, as the bounding
box around two regions can be easily derived from these.
In this paper, our final similarity measure is a combination o f the
above four:
s(ri, r j) = a1scolour (ri, r j) +a2stexture (ri, r j) +
a3ssize(ri, r j) +a4s f ill(ri, r j), (6)
where ai ∈ { 0, 1} denotes if the similarity measure is used or
not. As we aim to diversify our strategies, we do not consider any
weighted similarities.
Complementary Starting Regions. A third diversification
strategy is varying the complementary starting regions. To the
best of our knowledge, the method of [13] is the fastest, publ icly
available algorithm that yields high quality starting loca tions. We
could not find any other algorithm with similar computationa l effi-
ciency so we use only this oversegmentation in this paper. Bu t note
that different starting regions are (already) obtained by v arying the
colour spaces, each which has different invariance propert ies. Ad-
ditionally, we vary the threshold parameter k in [13].
3.3 Combining Locations
In this paper, we combine the object hypotheses of several va ria-
tions of our hierarchical grouping algorithm. Ideally, we w ant to
order the object hypotheses in such a way that the locations w hich
are most likely to be an object come first. This enables one to fi nd
a good trade-off between the quality and quantity of the resu lting
object hypothesis set, depending on the computational efficiency of
the subsequent feature extraction and classification metho d.
We choose to order the combined object hypotheses set based
on the order in which the hypotheses were generated in each in -
dividual grouping strategy. However, as we combine results from
up to 80 different strategies, such order would too heavily e mpha-
size large regions. To prevent this, we include some randomn ess
as follows. Given a grouping strategy j, let r j
i be the region which
is created at position i in the hierarchy, where i = 1 represents the
top of the hierarchy (whose corresponding region covers the com-
plete image). We now calculate the position value v j
i as RND × i,
where RND is a random number in range [0, 1]. The final ranking
is obtained by ordering the regions using v j
i .
When we use locations in terms of bounding boxes, we first rank
all the locations as detailed above. Only afterwards we filte r out
lower ranked duplicates. This ensures that duplicate boxes have a
better chance of obtaining a high rank. This is desirable bec ause
if multiple grouping strategies suggest the same box locati on, it is
likely to come from a visually coherent part of the image.
4 Object Recognition using Selective
Search
This paper uses the locations generated by our selective sea rch for
object recognition. This section details our framework for object
recognition.
Two types of features are dominant in object recognition: hi s-
tograms of oriented gradients (HOG) [8] and bag-of-words [7 , 27].
HOG has been shown to be successful in combination with the part-
based model by Felzenszwalb et al. [12]. However, as they use an
exhaustive search, HOG features in combination with a linea r clas-
sifier is the only feasible choice from a computational persp ective.
In contrast, our selective search enables the use of more exp ensive
and potentially more powerful features. Therefore we use ba g-of-
words for object recognition [16, 17, 34]. However, we use a m ore
powerful (and expensive) implementation than [16, 17, 34] b y em-
ploying a variety of colour-SIFT descriptors [32] and a finer spatial
pyramid division [18].
Specifically we sample descriptors at each pixel on a single s cale
(
σ = 1.2). Using software from [32], we extract SIFT [21] and two
colour SIFTs which were found to be the most sensitive for de-
tecting image structures, Extended OpponentSIFT [31] and R GB-
SIFT [32]. We use a visual codebook of size 4,000 and a spatial
pyramid with 4 levels using a 1x1, 2x2, 3x3. and 4x4 division.
This gives a total feature vector length of 360,000. In image clas-
sification, features of this size are already used [25, 37]. B ecause
a spatial pyramid results in a coarser spatial subdivision t han the
cells which make up a HOG descriptor, our features contain le ss
information about the specific spatial layout of the object. There-
fore, HOG is better suited for rigid objects and our features are
better suited for deformable object types.
As classifier we employ a Support V ector Machine with a his-
togram intersection kernel using the Shogun Toolbox [28]. T o ap-
ply the trained classifier, we use the fast, approximate classification
strategy of [22], which was shown to work well for Bag-of-Wor ds
in [30].
Our training procedure is illustrated in Figure 3. The initi al posi-
tive examples consist of all ground truth object windows. As initial
negative examples we select from all object locations gener ated
5

Figure 3: The training procedure of our object recognition p ipeline. As positive learning examples we use the ground tru th. As negatives
we use examples that have a 20-50% overlap with the positive e xamples. We iteratively add hard negatives using a retraini ng phase.
by our selective search that have an overlap of 20% to 50% with
a positive example. To avoid near-duplicate negative examp les,
a negative example is excluded if it has more than 70% overlap
with another negative. To keep the number of initial negativ es per
class below 20,000, we randomly drop half of the negatives fo r the
classes car, cat, dog and person. Intuitively, this set of examples
can be seen as difficult negatives which are close to the posit ive ex-
amples. This means they are close to the decision boundary an d are
therefore likely to become support vectors even when the com plete
set of negatives would be considered. Indeed, we found that t his
selection of training examples gives reasonably good initi al classi-
fication models.
Then we enter a retraining phase to iteratively add hard nega tive
examples (e.g. [12]): We apply the learned models to the training
set using the locations generated by our selective search. F or each
negative image we add the highest scoring location. As our in itial
training set already yields good models, our models converg e in
only two iterations.
For the test set, the final model is applied to all locations ge ner-
ated by our selective search. The windows are sorted by class ifier
score while windows which have more than 30% overlap with a
higher scoring window are considered near-duplicates and a re re-
moved.
5 Evaluation
In this section we evaluate the quality of our selective sear ch. We
divide our experiments in four parts, each spanning a separa te sub-
section:
Diversification Strategies. We experiment with a variety of
colour spaces, similarity measures, and thresholds of the i ni-
tial regions, all which were detailed in Section 3.2. We seek a
trade-off between the number of generated object hypothese s,
computation time, and the quality of object locations. We do
this in terms of bounding boxes. This results in a selection o f
complementary techniques which together serve as our final
selective search method.
Quality of Locations. We test the quality of the object location
hypotheses resulting from the selective search.
Object Recognition. We use the locations of our selective search
in the Object Recognition framework detailed in Section 4.
We evaluate performance on the Pascal VOC detection chal-
lenge.
An upper bound of location quality. We investigate how well
our object recognition framework performs when using an ob-
ject hypothesis set of “perfect” quality. How does this com-
pare to the locations that our selective search generates?
To evaluate the quality of our object hypotheses we define
the Average Best Overlap (ABO) and Mean Average Best Over-
lap (MABO) scores, which slightly generalises the measure u sed
in [9]. To calculate the Average Best Overlap for a specific cl ass c,
we calculate the best overlap between each ground truth anno tation
gc
i ∈ Gc and the object hypotheses L generated for the correspond-
ing image, and average:
ABO = 1
|Gc| ∑
gc
i ∈Gc
max
l j∈L
Overlap(gc
i , l j). (7)
The Overlap score is taken from [11] and measures the area of t he
intersection of two regions divided by its union:
Overlap(gc
i , l j) = area(gc
i ) ∩ area(lj)
area(gc
i ) ∪ area(lj) . (8)
Analogously to Average Precision and Mean Average Precisio n,
Mean Average Best Overlap is now defined as the mean ABO over
all classes.
Other work often uses the recall derived from the Pascal Over lap
Criterion to measure the quality of the boxes [1, 16, 34]. Thi s crite-
rion considers an object to be found when the Overlap of Equat ion
8 is larger than 0.5. However, in many of our experiments we ob -
tain a recall between 95% and 100% for most classes, making th is
measure too insensitive for this paper. However, we do repor t this
measure when comparing with other work.
To avoid overfitting, we perform the diversification strategies ex-
periments on the Pascal VOC 2007 TRAIN +VAL set. Other exper-
iments are done on the Pascal VOC 2007 TEST set. Additionally,
our object recognition system is benchmarked on the Pascal V OC
2010 detection challenge, using the independent evaluatio n server.
5.1 Diversification Strategies
In this section we evaluate a variety of strategies to obtain good
quality object location hypotheses using a reasonable numb er of
boxes computed within a reasonable amount of time.
5.1.1 Flat versus Hierarchy
In the description of our method we claim that using a full hie rar-
chy is more natural than using multiple flat partitionings by chang-
6

ing a threshold. In this section we test whether the use of a hi er-
archy also leads to better results. We therefore compare the use
of [13] with multiple thresholds against our proposed algor ithm.
Specifically, we perform both strategies in RGB colour space. For
[13], we vary the threshold from k = 50 to k = 1000 in steps of 50.
This range captures both small and large regions. Additiona lly, as a
special type of threshold, we include the whole image as an ob ject
location because quite a few images contain a single large ob ject
only. Furthermore, we also take a coarser range from k = 50 to
k = 950 in steps of 100. For our algorithm, to create initial regi ons
we use a threshold of k = 50, ensuring that both strategies have
an identical smallest scale. Additionally, as we generate f ewer re-
gions, we combine results using k = 50 and k = 100. As similarity
measure S we use the addition of all four similarities as defined in
Equation 6. Results are in table 2.
threshold k in [13] MABO # windows
Flat [13] k = 50, 150, · · ·, 950 0.659 387
Hierarchical (this paper) k = 50 0.676 395
Flat [13] k = 50, 100, · · ·, 1000 0.673 597
Hierarchical (this paper) k = 50, 100 0.719 625
Table 2: A comparison of multiple flat partitionings against hier-
archical partitionings for generating box locations shows that for
the hierarchical strategy the Mean Average Best Overlap (MA BO)
score is consistently higher at a similar number of location s.
As can be seen, the quality of object hypotheses is better for
our hierarchical strategy than for multiple flat partitioni ngs: At a
similar number of regions, our MABO score is consistently hi gher.
Moreover, the increase in MABO achieved by combining the lo-
cations of two variants of our hierarchical grouping algori thm is
much higher than the increase achieved by adding extra thres holds
for the flat partitionings. We conclude that using all locati ons from
a hierarchical grouping algorithm is not only more natural b ut also
more effective than using multiple flat partitionings.
5.1.2 Individual Diversification Strategies
In this paper we propose three diversification strategies to obtain
good quality object hypotheses: varying the colour space, v ary-
ing the similarity measures, and varying the thresholds to o btain
the starting regions. This section investigates the influen ce of each
strategy. As basic settings we use the RGB colour space, the com-
bination of all four similarity measures, and threshold k = 50. Each
time we vary a single parameter. Results are given in Table 3.
We start examining the combination of similarity measures o n
the left part of Table 3. Looking first at colour, texture, siz e, and fill
individually, we see that the texture similarity performs w orst with
a MABO of 0.581, while the other measures range between 0.63
and 0.64. To test if the relatively low score of texture is due to our
choice of feature, we also tried to represent texture by Local Binary
Patterns [24]. We experimented with 4 and 8 neighbours on dif -
ferent scales using different uniformity/consistency of t he patterns
(see [24]), where we concatenate LBP histograms of the indiv idual
colour channels. However, we obtained similar results (MAB O of
0.577). We believe that one reason of the weakness of texture is be-
cause of object boundaries: When two segments are separated b y
an object boundary, both sides of this boundary will yield si milar
edge-responses, which inadvertently increases similarit y.
Similarities MABO # box Colours MABO # box
C 0.635 356 HSV 0.693 463
T 0.581 303 I 0.670 399
S 0.640 466 RGB 0.676 395
F 0.634 449 rgI 0.693 362
C+T 0.635 346 Lab 0.690 328
C+S 0.660 383 H 0.644 322
C+F 0.660 389 rgb 0.647 207
T+S 0.650 406 C 0.615 125
T+F 0.638 400 Thresholds MABO # box
S+F 0.638 449 50 0.676 395
C+T+S 0.662 377 100 0.671 239
C+T+F 0.659 381 150 0.668 168
C+S+F 0.674 401 250 0.647 102
T+S+F 0.655 427 500 0.585 46
C+T+S+F 0.676 395 1000 0.477 19
Table 3: Mean Average Best Overlap for box-based object hy-
potheses using a variety of segmentation strategies. (C)ol our,
(S)ize, and (F)ill perform similar. (T)exture by itself is w eak. The
best combination is as many diverse sources as possible.
While the texture similarity yields relatively few object lo ca-
tions, at 300 locations the other similarity measures still yield a
MABO higher than 0.628. This suggests that when comparing
individual strategies the final MABO scores in table 3 are goo d
indicators of trade-off between quality and quantity of the object
hypotheses. Another observation is that combinations of si milarity
measures generally outperform the single measures. In fact , us-
ing all four similarity measures perform best yielding a MAB O of
0.676.
Looking at variations in the colour space in the top-right of Table
3, we observe large differences in results, ranging from a MA BO
of 0.615 with 125 locations for the C colour space to a MABO of
0.693 with 463 locations for the HSV colour space. We note tha t
Lab-space has a particularly good MABO score of 0.690 using only
328 boxes. Furthermore, the order of each hierarchy is effec tive:
using the first 328 boxes of HSV colour space yields 0.690 MABO ,
while using the first 100 boxes yields 0.647 MABO. This shows
that when comparing single strategies we can use only the MAB O
scores to represent the trade-off between quality and quant ity of
the object hypotheses set. We will use this in the next sectio n when
finding good combinations.
Experiments on the thresholds of [13] to generate the starti ng
regions show, in the bottom-right of Table 3, that a lower ini tial
threshold results in a higher MABO using more object locatio ns.
5.1.3 Combinations of Diversification Strategies
We combine object location hypotheses using a variety of com -
plementary grouping strategies in order to get a good qualit y set
of object locations. As a full search for the best combinatio n is
computationally expensive, we perform a greedy search usin g the
MABO score only as optimization criterion. We have earlier o b-
served that this score is representative for the trade-off b etween the
number of locations and their quality.
From the resulting ordering we create three configurations: a
single best strategy, a fast selective search, and a quality selective
search using all combinations of individual components, i.e. colour
7

Diversification
V ersion Strategies MABO # win # strategies time (s)
Single HSV
Strategy C+T+S+F 0.693 362 1 0.71
k = 100
Selective HSV , Lab
Search C+T+S+F, T+S+F 0.799 2147 8 3.79
Fast k = 50, 100
Selective HSV , Lab, rgI, H, I
Search C+T+S+F, T+S+F, F, S 0.878 10,108 80 17.15
Quality k = 50, 100, 150, 300
Table 4: Our selective search methods resulting from a greed y
search. We take all combinations of the individual diversifi ca-
tion strategies selected, resulting in 1, 8, and 80 variants of our
hierarchical grouping algorithm. The Mean Average Best Ove r-
lap (MABO) score keeps steadily rising as the number of windo ws
increase.
method recall MABO # windows
Arbelaez et al. [3] 0.752 0.649 ± 0.193 418
Alexe et al. [2] 0.944 0.694 ± 0.111 1,853
Harzallah et al. [16] 0.830 - 200 per class
Carreira and Sminchisescu [4] 0.879 0.770 ± 0.084 517
Endres and Hoiem [9] 0.912 0.791 ± 0.082 790
Felzenszwalb et al. [12] 0.933 0.829 ± 0.052 100,352 per class
V edaldiet al. [34] 0.940 - 10,000 per class
Single Strategy 0.840 0.690 ± 0.171 289
Selective search “Fast” 0.980 0.804 ± 0.046 2,134
Selective search “Quality” 0.991 0.879 ± 0.039 10,097
Table 5: Comparison of recall, Mean Average Best Overlap
(MABO) and number of window locations for a variety of meth-
ods on the Pascal 2007 TEST set.
space, similarities, thresholds, as detailed in Table 4. Th e greedy
search emphasizes variation in the combination of similari ty mea-
sures. This confirms our diversification hypothesis: In the q uality
version, next to the combination of all similarities, Fill a nd Size
are taken separately. The remainder of this paper uses the th ree
strategies in Table 4.
5.2 Quality of Locations
In this section we evaluate our selective search algorithms in terms
of both Average Best Overlap and the number of locations on th e
Pascal VOC 2007 TEST set. We first evaluate box-based locations
and afterwards briefly evaluate region-based locations.
5.2.1 Box-based Locations
We compare with the sliding window search of [16], the slidin g
window search of [12] using the window ratio’s of their model s,
the jumping windows of [34], the “objectness” boxes of [2], t he
boxes around the hierarchical segmentation algorithm of [3 ], the
boxes around the regions of [9], and the boxes around the regi ons
of [4]. From these algorithms, only [3] is not designed for fin ding
object locations. Y et [3] is one of the best contour detector s pub-
licly available, and results in a natural hierarchy of regio ns. We
include it in our evaluation to see if this algorithm designe d for
segmentation also performs well on finding good object locat ions.
Furthermore, [4, 9] are designed to find good object regions r ather
then boxes. Results are shown in Table 5 and Figure 4.
As shown in Table 5, our “Fast” and “Quality” selective searc h
methods yield a close to optimal recall of 98% and 99% respec-
tively. In terms of MABO, we achieve 0.804 and 0.879 respec-
tively. To appreciate what a Best Overlap of 0.879 means, Fig ure
5 shows for bike, cow, and person an example location which has
an overlap score between 0.874 and 0.884. This illustrates t hat our
selective search yields high quality object locations.
Furthermore, note that the standard deviation of our MABO
scores is relatively low: 0.046 for the fast selective searc h, and
0.039 for the quality selective search. This shows that sele ctive
search is robust to difference in object properties, and als o to im-
age condition often related with specific objects (one examp le is
indoor/outdoor lighting).
If we compare with other algorithms, the second highest reca ll is
at 0.940 and is achieved by the jumping windows [34] using 10,000
boxes per class. As we do not have the exact boxes, we were unable
to obtain the MABO score. This is followed by the exhaustive
search of [12] which achieves a recall of 0.933 and a MABO of
0.829 at 100,352 boxes per class (this number is the average over
all classes). This is significantly lower then our method whi le using
at least a factor of 10 more object locations.
Note furthermore that the segmentation methods of [4, 9] hav e
a relatively high standard deviation. This illustrates tha t a single
strategy can not work equally well for all classes. Instead, using
multiple complementary strategies leads to more stable and reliable
results.
If we compare the segmentation of Arbelaez [3] with a the sin-
gle best strategy of our method, they achieve a recall of 0.75 2 and
a MABO of 0.649 at 418 boxes, while we achieve 0.875 recall
and 0.698 MABO using 286 boxes. This suggests that a good seg-
mentation algorithm does not automatically result in good o bject
locations in terms of bounding boxes.
Figure 4 explores the trade-off between the quality and quan tity
of the object hypotheses. In terms of recall, our “Fast” meth od out-
performs all other methods. The method of [16] seems competi tive
for the 200 locations they use, but in their method the number of
boxes is per class while for our method the same boxes are used for
all classes. In terms of MABO, both the object hypotheses gen era-
tion method of [4] and [9] have a good quantity/quality trade-off for
the up to 790 object-box locations per image they generate. H ow-
ever, these algorithms are computationally 114 and 59 times more
expensive than our “Fast” method.
Interestingly, the “objectness” method of [2] performs quite well
in terms of recall, but much worse in terms of MABO. This is
most likely caused by their non-maximum suppression, which sup-
presses windows which have more than an 0.5 overlap score wit h
an existing, higher ranked window. And while this significan tly
improved results when a 0.5 overlap score is the definition of find-
ing an object, for the general problem of finding the highest q uality
locations this strategy is less effective and can even be har mful by
eliminating better locations.
Figure 6 shows for several methods the Average Best Overlap
per class. It is derived that the exhaustive search of [12] wh ich
uses 10 times more locations which are class specific, perfor ms
similar to our method for the classes bike, table, chair , and sofa,
for the other classes our method yields the best score. In gen eral,
the classes with the highest scores are cat, dog, horse, and sofa,
which are easy largely because the instances in the dataset t end
to be big. The classes with the lowest scores are bottle, person,
and plant, which are difficult because instances tend to be small.
8

0 500 1000 1500 2000 2500 3000
0.5
0.55
0.6
0.65
0.7
0.75
0.8
0.85
0.9
0.95
1
Number of Object Boxes
Recall
 
 
Harzallah et al.
Vedaldi et al.
Alexe et al.
Carreira and Sminchisescu
Endres and Hoiem
Selective search Fast
Selective search Quality
(a) Trade-off between number of object locations and the Pasc al Recall criterion.
0 500 1000 1500 2000 2500 3000
0.5
0.55
0.6
0.65
0.7
0.75
0.8
0.85
0.9
0.95
1
Number of Object Boxes
Mean Average Best Overlap
 
 
Alexe et al.
Carreira and Sminchisescu
Endres and Hoiem
Selective search Fast
Selective search Quality
(b) Trade-off between number of object locations and the MABO score.
Figure 4: Trade-off between quality and quantity of the obje ct hypotheses in terms of bounding boxes on the Pascal 2007 TEST set. The
dashed lines are for those methods whose quantity is express ed is the number of boxes per class . In terms of recall “Fast” selective
search has the best trade-off. In terms of Mean Average Best O verlap the “Quality” selective search is comparable with [4 , 9] yet is
much faster to compute and goes on longer resulting in a highe r final MABO of 0.879.
(a) Bike: 0.863
 (b) Cow: 0.874
 (c) Chair: 0.884
 (d) Person: 0.882
 (e) Plant: 0.873
Figure 5: Examples of locations for objects whose Best Overl ap score is around our Mean Average Best Overlap of 0.879. The green
boxes are the ground truth. The red boxes are created using th e “Quality” selective search.
9

0.5
0.55
0.6
0.65
0.7
0.75
0.8
0.85
0.9
0.95
1
Average Best Overlap
 
 
plane
bike
bird
boat
bottle
bus
car
cat
chair
cow
table
dog
horse
motor
person
plant
sheep
sofa
train
tv
Alexe et al.
Endres and Hoiem
Carreira and Sminchisescu
Felzenszwalb et al.
Selective search Fast
Selective search Quality
Figure 6: The Average Best Overlap scores per class for sever al method for generating box-based object locations on Pasc al VOC 2007
TEST . For all classes but table our “Quality” selective search yields the best locations. F or 12 out of 20 classes our “Fast” selective
search outperforms the expensive [4, 9]. We always outperfo rm [2].
Nevertheless, cow, sheep, and tv are not bigger than person and yet
can be found quite well by our algorithm.
To summarize, selective search is very effective in finding a high
quality set of object hypotheses using a limited number of bo xes,
where the quality is reasonable consistent over the object c lasses.
The methods of [4] and [9] have a similar quality/quantity tr ade-off
for up to 790 object locations. However, they have more varia tion
over the object classes. Furthermore, they are at least 59 an d 13
times more expensive to compute for our “Fast” and “Quality” se-
lective search methods respectively, which is a problem for current
dataset sizes for object recognition. In general, we conclu de that
selective search yields the best quality locations at 0.879 MABO
while using a reasonable number of 10,097 class-independen t ob-
ject locations.
5.2.2 Region-based Locations
In this section we examine how well the regions that our selective
search generates captures object locations. We do this on th e seg-
mentation part of the Pascal VOC 2007 TEST set. We compare with
the segmentation of [3] and with the object hypothesis regio ns of
both [4, 9]. Table 6 shows the results. Note that the number of
regions is larger than the number of boxes as there are almost no
exact duplicates.
The object regions of both [4, 9] are of similar quality as our
“Fast” selective search, 0.665 MABO and 0.679 MABO respec-
tively where our “Fast” search yields 0.666 MABO. While [4, 9]
use fewer regions these algorithms are respectively 114 and 59
times computationally more expensive. Our “Quality” selec tive
search generates 22,491 regions and is respectively 25 and 13 times
faster than [4, 9], and has by far the highest score of 0.730 MA BO.
method recall MABO # regions time(s

[... truncated for benchmark fixture size — see script body_max_chars ...]


## References

[1] B. Alexe, T. Deselaers, and V . Ferrari. What is an object? I n
CVPR, 2010. 2, 6
[2] B. Alexe, T. Deselaers, and V . Ferrari. Measuring the ob-
jectness of image windows. IEEE transactions on Pattern
Analysis and Machine Intelligence , 2012. 3, 8, 10, 13
[3] P . Arbel ́aez, M. Maire, C. Fowlkes, and J. Malik. Contour
detection and hierarchical image segmentation. TPAMI, 2011.
1, 2, 3, 4, 8, 10, 11
[4] J. Carreira and C. Sminchisescu. Constrained parametri c min-
cuts for automatic object segmentation. In CVPR, 2010. 2, 3,
8, 9, 10, 11, 13
[5] O. Chum and A. Zisserman. An exemplar model for learning
object classes. In CVPR, 2007. 3
[6] D. Comaniciu and P . Meer. Mean shift: a robust approach
toward feature space analysis. TPAMI, 24:603–619, 2002. 1,
3
[7] G. Csurka, C. R. Dance, L. Fan, J. Willamowski, and C. Bray .
Visual categorization with bags of keypoints. In ECCV Sta-
tistical Learning in Computer Vision , 2004. 5
13

[8] N. Dalal and B. Triggs. Histograms of oriented gradients for
human detection. In CVPR, 2005. 1, 2, 3, 5
[9] I. Endres and D. Hoiem. Category independent object pro-
posals. In ECCV, 2010. 2, 3, 6, 8, 9, 10, 11, 13
[10] M. Everingham, L. V . Gool, C. Williams, J. Winn, and A. Zis-
serman. Overview and results of the detection challenge. Th e
Pascal Visual Object Classes Challenge Workshop, 2011. 12
[11] M. Everingham, L. van Gool, C. K. I. Williams, J. Winn, an d
A. Zisserman. The pascal visual object classes (voc) chal-
lenge. IJCV, 88:303–338, 2010. 6
[12] P . F. Felzenszwalb, R. B. Girshick, D. McAllester, and D. Ra-
manan. Object detection with discriminatively trained par t
based models. TPAMI, 32:1627–1645, 2010. 1, 2, 3, 5, 6, 8,
11, 12, 13
[13] P . F. Felzenszwalb and D. P . Huttenlocher. Efficient Gra ph-
Based Image Segmentation. IJCV, 59:167–181, 2004. 1, 3,
4, 5, 7
[14] J. M. Geusebroek, R. van den Boomgaard, A. W. M. Smeul-
ders, and H. Geerts. Color invariance. TPAMI, 23:1338–1350,
2001. 4
[15] C. Gu, J. J. Lim, P . Arbel ́aez, and J. Malik. Recognition using
regions. In CVPR, 2009. 2
[16] H. Harzallah, F. Jurie, and C. Schmid. Combining efficie nt
object localization and image classification. In ICCV, 2009.
1, 2, 3, 5, 6, 8
[17] C. H. Lampert, M. B. Blaschko, and T. Hofmann. Efficient
subwindow search: A branch and bound framework for object
localization. TPAMI, 31:2129–2142, 2009. 2, 5
[18] S. Lazebnik, C. Schmid, and J. Ponce. Beyond bags of fea-
tures: Spatial pyramid matching for recognizing natural scene
categories. In CVPR, 2006. 5
[19] F. Li, J. Carreira, and C. Sminchisescu. Object recogni tion as
ranking holistic figure-ground hypotheses. In CVPR, 2010. 2
[20] C. Liu, L. Sharan, E.H. Adelson, and R. Rosenholtz. Ex-
ploring features in a bayesian framework for material recog -
nition. In Computer Vision and Pattern Recognition 2010 .
IEEE, 2010. 4
[21] D. G. Lowe. Distinctive image features from scale-inva riant
keypoints. IJCV, 60:91–110, 2004. 5, 13
[22] S. Maji, A. C. Berg, and J. Malik. Classification using in ter-
section kernel support vector machines is efficient. In CVPR,
2008. 5
[23] S. Maji and J. Malik. Object detection using a max-margi n
hough transform. In CVPR, 2009. 3
[24] T. Ojala, M. Pietikainen, and T. Maenpaa. Multiresolut ion
gray-scale and rotation invariant texture classification w ith
local binary patterns. Pattern Analysis and Machine Intel-
ligence, IEEE Transactions on, 24(7):971–987, 2002. 7
[25] Florent Perronnin, Jorge S ́anchez, and Thomas Mensink. Im-
proving the Fisher Kernel for Large-Scale Image Classifica-
tion. In ECCV, 2010. 5
[26] J. Shi and J. Malik. Normalized cuts and image segmentat ion.
TPAMI, 22:888–905, 2000. 1
[27] J. Sivic and A. Zisserman. Video google: A text retrieva l
approach to object matching in videos. In ICCV, 2003. 5
[28] Soeren Sonnenburg, Gunnar Raetsch, Sebastian Hensche l,
Christian Widmer, Jonas Behr, Alexander Zien, Fabio
de Bona, Alexander Binder, Christian Gehl, and V ojtech
Franc. The shogun machine learning toolbox. JMLR,
11:1799–1802, 2010. 5
[29] Z. Tu, X. Chen, A. L. Y uille, and S. Zhu. Image parsing: Un i-
fying segmentation, detection and recognition. International
Journal of Computer Vision, Marr Prize Issue, 2005. 1
[30] J.R.R. Uijlings, A.W.M. Smeulders, and R.J.H. Scha. Re al-
time visual concept classification. IEEE Transactions on Mul-
timedia, In press, 2010. 5, 12
[31] K. E. A. van de Sande and T. Gevers. Illumination-invari ant
descriptors for discriminative visual object categorizat ion.
Technical report, University of Amsterdam, 2012. 5
[32] K. E. A. van de Sande, T. Gevers, and C. G. M. Snoek.
Evaluating color descriptors for object and scene recognit ion.
TPAMI, 32:1582–1596, 2010. 5, 12
[33] K. E. A. van de Sande, T. Gevers, and C. G. M. Snoek.
Empowering visual categorization with the GPU. TMM,
13(1):60–70, 2011. 11
[34] A. V edaldi, V . Gulshan, M. V arma, and A. Zisserman. Mul-
tiple kernels for object detection. In ICCV, 2009. 3, 5, 6,
8
[35] P . Viola and M. Jones. Rapid object detection using a boo sted
cascade of simple features. In CVPR, volume 1, pages 511–
518, 2001. 1
[36] P . Viola and M. J. Jones. Robust real-time face detectio n.
IJCV, 57:137–154, 2004. 2, 3
[37] Xi Zhou, Kai Y u, Tong Zhang, and Thomas S. Huang. Im-
age classification using super-vector coding of local image
descriptors. In ECCV, 2010. 5
[38] L. Zhu, Y . Chen, A. Y uille, and W. Freeman. Latent hierarchi-
cal structural learning for object detection. In CVPR, 2010.
13
14