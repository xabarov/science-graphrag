# 1

Object Detection with Discriminatively Trained
Part Based Models
Pedro F . Felzenszwalb, Ross B. Girshick, David McAllester and Deva Ramanan

## Abstract

We describe an object detection system based on mixtures of multiscale deformable part models. Our system is able
to represent highly variable object classes and achieves state-of-the-art results in the PASCAL object detection challenges. While
deformable part models have become quite popular, their value had not been demonstrated on difficult benchmarks such as the
PASCAL datasets. Our system relies on new methods for discriminative training with partially labeled data. We combine a margin-
sensitive approach for data-mining hard negative examples with a formalism we call latent SVM . A latent SVM is a reformulation of
MI-SVM in terms of latent variables. A latent SVM is semi-convex and the training problem becomes convex once latent information is
specified for the positive examples. This leads to an iterative training algorithm that alternates between fixing latent values for positive
examples and optimizing the latent SVM objective function.
Index Terms—Object Recognition, Deformable Models, Pictorial Structures, Discriminative Training, Latent SVM
!

## Body

1 I NTRODUCTION
Object recognition is one of the fundamental challenges
in computer vision. In this paper we consider the prob-
lem of detecting and localizing generic objects from
categories such as people or cars in static images. This
is a difficult problem because objects in such categories
can vary greatly in appearance. Variations arise not only
from changes in illumination and viewpoint, but also
due to non-rigid deformations, and intraclass variability
in shape and other visual properties. For example, peo-
ple wear different clothes and take a variety of poses
while cars come in a various shapes and colors.
We describe an object detection system that represents
highly variable objects using mixtures of multiscale de-
formable part models. These models are trained using
a discriminative procedure that only requires bounding
boxes for the objects in a set of images. The resulting
system is both efficient and accurate, achieving state-of-
the-art results on the PASCAL VOC benchmarks [11]–
[13] and the INRIA Person dataset [10].
Our approach builds on the pictorial structures frame-
work [15], [20]. Pictorial structures represent objects by
a collection of parts arranged in a deformable configu-
ration. Each part captures local appearance properties of
an object while the deformable configuration is charac-
terized by spring-like connections between certain pairs
of parts.
Deformable part models such as pictorial structures
provide an elegant framework for object detection. Yet
• P .F. Felzenszwalb is with the Department of Computer Science, University
of Chicago. E-mail: pff@cs.uchicago.edu
• R.B. Girshick is with the Department of Computer Science, University of
Chicago. E-mail: rbg@cs.uchicago.edu
• D. McAllester is with the Toyota Technological Institute at Chicago. E-
mail: mcallester@tti-c.org
• D. Ramanan is with the Department of Computer Science, UC Irvine.
E-mail: dramanan@ics.uci.edu
it has been difficult to establish their value in practice.
On difficult datasets deformable part models are often
outperformed by simpler models such as rigid templates
[10] or bag-of-features [44]. One of the goals of our work
is to address this performance gap.
While deformable models can capture significant vari-
ations in appearance, a single deformable model is often
not expressive enough to represent a rich object category.
Consider the problem of modeling the appearance of bi-
cycles in photographs. People build bicycles of different
types (e.g., mountain bikes, tandems, and 19th-century
cycles with one big wheel and a small one) and view
them in various poses (e.g., frontal versus side views).
The system described here uses mixture models to deal
with these more significant variations.
We are ultimately interested in modeling objects using
“visual grammars”. Grammar based models (e.g. [16],
[24], [45]) generalize deformable part models by rep-
resenting objects using variable hierarchical structures.
Each part in a grammar based model can be defined
directly or in terms of other parts. Moreover, grammar
based models allow for, and explicitly model, structural
variations. These models also provide a natural frame-
work for sharing information and computation between
different object classes. For example, different models
might share reusable parts.
Although grammar based models are our ultimate
goal, we have adopted a research methodology under
which we gradually move toward richer models while
maintaining a high level of performance. Improving
performance by enriched models is surprisingly difficult.
Simple models have historically outperformed sophis-
ticated models in computer vision, speech recognition,
machine translation and information retrieval. For ex-
ample, until recently speech recognition and machine
translation systems based on n-gram language models
outperformed systems based on grammars and phrase

2
structure. In our experience maintaining performance
seems to require gradual enrichment of the model.
One reason why simple models can perform better in
practice is that rich models often suffer from difficulties
in training. For object detection, rigid templates and bag-
of-features models can be easily trained using discrimi-
native methods such as support vector machines (SVM).
Richer models are more difficult to train, in particular
because they often make use of latent information.
Consider the problem of training a part-based model
from images labeled only with bounding boxes around
the objects of interest. Since the part locations are not
labeled, they must be treated as latent (hidden) variables
during training. More complete labeling might support
better training, but it can also result in inferior training
if the labeling used suboptimal parts. Automatic part
labeling has the potential to achieve better performance
by automatically finding effective parts. More elaborate
labeling is also time consuming and expensive.
The Dalal-Triggs detector [10], which won the 2006
PASCAL object detection challenge, used a single filter
on histogram of oriented gradients (HOG) features to
represent an object category. This detector uses a slid-
ing window approach, where a filter is applied at all
positions and scales of an image. We can think of the
detector as a classifier which takes as input an image,
a position within that image, and a scale. The classifier
determines whether or not there is an instance of the
target category at the given position and scale. Since
the model is a simple filter we can compute a score
as β· Φ(x) where β is the filter, x is an image with a
specified position and scale, and Φ(x) is a feature vector.
A major innovation of the Dalal-Triggs detector was the
construction of particularly effective features.
Our first innovation involves enriching the Dalal-
Triggs model using a star-structured part-based model
defined by a “root” filter (analogous to the Dalal-Triggs
filter) plus a set of parts filters and associated deforma-
tion models. The score of one of our star models at a
particular position and scale within an image is the score
of the root filter at the given location plus the sum over
parts of the maximum, over placements of that part, of
the part filter score on its location minus a deformation
cost measuring the deviation of the part from its ideal
location relative to the root. Both root and part filter
scores are defined by the dot product between a filter (a
set of weights) and a subwindow of a feature pyramid
computed from the input image. Figure 1 shows a star
model for the person category.
In our models the part filters capture features at twice
the spatial resolution relative to the features captured by
the root filter. In this way we model visual appearance
at multiple scales.
To train models using partially labeled data we use a
latent variable formulation of MI-SVM [3] that we call
latent SVM (LSVM). In a latent SVM each example x is
(a) (b) (c)
Fig. 1. Detections obtained with a single component
person model. The model is defined by a coarse root filter
(a), several higher resolution part filters (b) and a spatial
model for the location of each part relative to the root
(c). The filters specify weights for histogram of oriented
gradients features. Their visualization show the positive
weights at different orientations. The visualization of the
spatial models reflects the “cost” of placing the center of
a part at different locations relative to the root.
scored by a function of the following form,
fβ(x) = max
z∈Z(x)
β· Φ(x, z). (1)
Here β is a vector of model parameters, z are latent
values, and Φ(x, z) is a feature vector. In the case of one
of our star models β is the concatenation of the root
filter, the part filters, and deformation cost weights, z is
a specification of the object configuration, and Φ(x, z) is
a concatenation of subwindows from a feature pyramid
and part deformation features.
We note that (1) can handle very general forms of
latent information. For example, z could specify a deriva-
tion under a rich visual grammar.
Our second class of models represents an object cate-
gory by a mixture of star models. The score of a mixture
model at a particular position and scale is the maximum
over components, of the score of that component model
at the given location. In this case the latent information,
z, specifies a component label and a configuration for
that component. Figure 2 shows a mixture model for the
bicycle category.
To obtain high performance using discriminative train-
ing it is often important to use large training sets. In the
case of object detection the training problem is highly un-
balanced because there is vastly more background than
objects. This motivates a process of searching through

3
Fig. 2. Detections obtained with a 2 component bicycle model. These examples illustrate the importance of
deformations mixture models. In this model the first component captures sideways views of bicycles while the second
component captures frontal and near frontal views. The sideways component can deform to match a “wheelie”.
the background data to find a relatively small number
of potential false positives, or hard negative examples.
A methodology of data-mining for hard negative ex-
amples was adopted by Dalal and Triggs [10] but goes
back at least to the bootstrapping methods used by [38]
and [35]. Here we analyze data-mining algorithms for
SVM and LSVM training. We prove that data-mining
methods can be made to converge to the optimal model
defined in terms of the entire training set.
Our object models are defined by filters that score
subwindows of a feature pyramid. We have investigated
feature sets similar to the HOG features from [10] and
found lower dimensional features which perform as well
as the original ones. By doing principal component anal-
ysis on HOG features the dimensionality of the feature
vector can be significantly reduced with no noticeable
loss of information. Moreover, by examining the prin-
cipal eigenvectors we discover structure that leads to
“analytic” versions of low-dimensional features which
are easily interpretable and can be computed efficiently.
We have also considered some specific problems that
arise in the PASCAL object detection challenge and sim-
ilar datasets. We show how the locations of parts in an
object hypothesis can be used to predict a bounding box
for the object. This is done by training a model specific
predictor using least-squares regression. We also demon-
strate a simple method for aggregating the output of
several object detectors. The basic idea is that objects of
some categories provide evidence for, or against, objects
of other categories in the same image. We exploit this
idea by training a category specific classifier that rescores
every detection of that category using its original score
and the highest scoring detection from each of the other
categories.
2 R ELATED WORK
There is a significant body of work on deformable mod-
els of various types for object detection, including several
kinds of deformable template models (e.g. [7], [8], [21],
[43]), and a variety of part-based models (e.g. [2], [6], [9],
[15], [18], [20], [28], [42]).
In the constellation models from [18], [42] parts are
constrained to be in a sparse set of locations determined
by an interest point operator, and their geometric ar-
rangement is captured by a Gaussian distribution. In
contrast, pictorial structure models [15], [20] define a
matching problem where parts have an individual match
cost in a dense set of locations, and their geometric
arrangement is captured by a set of “springs” connecting
pairs of parts. The patchwork of parts model from [2] is
similar, but it explicitly considers how the appearance
model of overlapping parts interact.
Our models are largely based on the pictorial struc-
tures framework from [15], [20]. We use a dense set of
possible positions and scales in an image, and define
a score for placing a filter at each of these locations.

4
The geometric configuration of the filters is captured by
a set of deformation costs (“springs”) connecting each
part filter to the root filter, leading to a star-structured
pictorial structure model. Note that we do not model
interactions between overlapping parts. While we might
benefit from modeling such interactions, this does not
appear to be a problem when using models trained with
a discriminative procedure, and it significantly simplifies
the problem of matching a model to an image.
The introduction of new local and semi-local features
has played an important role in advancing the perfor-
mance of object recognition methods. These features are
typically invariant to illumination changes and small
deformations. Many recent approaches use wavelet-like
features [30], [41] or locally-normalized histograms of
gradients [10], [29]. Other methods, such as [5], learn
dictionaries of local structures from training images. In
our work, we use histogram of gradient (HOG) features
from [10] as a starting point, and introduce a variation
that reduces the feature size with no loss in performance.
As in [26] we used principal component analysis (PCA)
to discover low dimensional features, but we note that
the eigenvectors we obtain have a clear structure that
leads to a new set of “analytic” features. This removes
the need to perform a costly projection step when com-
puting dense feature maps.
Significant variations in shape and appearance, such as
caused by extreme viewpoint changes, are not well cap-
tured by a 2D deformable model. Aspect graphs [31] are
a classical formalism for capturing significant changes
that are due to viewpoint variation. Mixture models
provide a simpler alternative approach. For example, it
is common to use multiple templates to encode frontal
and side views of faces and cars [36]. Mixture models
have been used to capture other aspects of appearance
variation as well, such as when there are multiple natural
subclasses in an object category [5].
Matching a deformable model to an image is a diffi-
cult optimization problem. Local search methods require
initialization near the correct solution [2], [7], [43]. To
guarantee a globally optimal match, more aggressive
search is needed. One popular approach for part-based
models is to restrict part locations to a small set of
possible locations returned by an interest point detector
[1], [18], [42]. Tree (and star) structured pictorial structure
models [9], [15], [19] allow for the use of dynamic
programming and generalized distance transforms to
efficiently search over all possible object configurations
in an image, without restricting the possible locations
for each part. We use these techniques for matching our
models to images.
Part-based deformable models are parameterized by
the appearance of each part and a geometric model
capturing spatial relationships among parts. For gen-
erative models one can learn model parameters using
maximum likelihood estimation. In a fully-supervised
setting training images are labeled with part locations
and models can often be learned using simple methods
[9], [15]. In a weakly-supervised setting training images
may not specify locations of parts. In this case one can
simultaneously estimate part locations and learn model
parameters with EM [2], [18], [42].
Discriminative training methods select model param-
eters so as to minimize the mistakes of a detection algo-
rithm on a set of training images. Such approaches di-
rectly optimize the decision boundary between positive
and negative examples. We believe this is one reason for
the success of simple models trained with discriminative
methods, such as the Viola-Jones [41] and Dalal-Triggs
[10] detectors. It has been more difficult to train part-
based models discriminatively, though strategies exist
[4], [23], [32], [34].
Latent SVMs are related to hidden CRFs [32]. How-
ever, in a latent SVM we maximize over latent part loca-
tions as opposed to marginalizing over them, and we use
a hinge-loss rather than log-loss in training. This leads
to an an efficient coordinate-descent style algorithm for
training, as well as a data-mining algorithm that allows
for learning with very large datasets. A latent SVM can
be viewed as a type of energy-based model [27].
A latent SVM is equivalent to the MI-SVM formulation
of multiple instance learning (MIL) in [3], but we find
the latent variable formulation more natural for the prob-
lems we are interested in. 1 A different MIL framework
was previously used for training object detectors with
weakly labeled data in [40].
Our method for data-mining hard examples during
training is related to working set methods for SVMs (e.g.
[25]). The approach described here requires relatively
few passes through the complete set of training examples
and is particularly well suited for training with very
large data sets, where only a fraction of the examples
can fit in RAM.
The use of context for object detection and recognition
has received increasing attention in the recent years.
Some methods (e.g. [39]) use low-level holistic image fea-
tures for defining likely object hypothesis. The method
in [22] uses a coarse but semantically rich representation
of a scene, including its 3D geometry, estimated using a
variety of techniques. Here we define the context of an
image using the results of running a variety of object
detectors in the image. The idea is related to [33] where
a CRF was used to capture co-occurrences of objects,
although we use a very different approach to capture
this information.
A preliminary version of our system was described in
[17]. The system described here differs from the one in
[17] in several ways, including: the introduction of mix-
ture models; here we optimize the true latent SVM ob-
jective function using stochastic gradient descent, while
in [17] we used an SVM package to optimize a heuristic
approximation of the objective; here we use new features
that are both lower-dimensional and more informative;
1. We defined a latent SVM in [17] before realizing the relationship
to MI-SVM.

5
Feature pyramid
Image pyramid
Fig. 3. A feature pyramid and an instantiation of a person
model within that pyramid. The part filters are placed at
twice the spatial resolution of the placement of the root.
we now post-process detections via bounding box pre-
diction and context rescoring.
3 M ODELS
All of our models involve linear filters that are applied
to dense feature maps. A feature map is an array whose
entries are d-dimensional feature vectors computed from
a dense grid of locations in an image. Intuitively each
feature vector describes a local image patch. In practice
we use a variation of the HOG features from [10], but the
framework described here is independent of the specific
choice of features.
A filter is a rectangular template defined by an array
of d-dimensional weight vectors. The response, or score,
of a filter F at a position (x, y) in a feature map G is
the “dot product” of the filter and a subwindow of the
feature map with top-left corner at (x, y),
∑
x′,y′
F [x′, y′]· G[x + x′, y + y′].
We would like to define a score at different positions
and scales in an image. This is done using a feature
pyramid, which specifies a feature map for a finite
number of scales in a fixed range. In practice we com-
pute feature pyramids by computing a standard image
pyramid via repeated smoothing and subsampling, and
then computing a feature map from each level of the
image pyramid. Figure 3 illustrates the construction.
The scale sampling in a feature pyramid is determined
by a parameter λ defining the number of levels in an
octave. That is, λ is the number of levels we need to go
down in the pyramid to get to a feature map computed
at twice the resolution of another one. In practice we
have used λ = 5 in training and λ = 10 at test time. Fine
sampling of scale space is important for obtaining high
performance with our models.
The system in [10] uses a single filter to define an
object model. That system detects objects from a par-
ticular category by computing the score of the filter at
each position and scale of a HOG feature pyramid and
thresholding the scores.
Let F be a w× h filter. Let H be a feature pyramid
and p = ( x, y, l) specify a position (x, y) in the l-th
level of the pyramid. Let φ(H, p, w, h) denote the vector
obtained by concatenating the feature vectors in the w×h
subwindow of H with top-left corner at p in row-major
order. The score of F at p is F′· φ(H, p, w, h), where F′ is
the vector obtained by concatenating the weight vectors
in F in row-major order. Below we write F′·φ(H, p) since
the subwindow dimensions are implicitly defined by the
dimensions of the filter F .
3.1 Deformable Part Models
Our star models are defined by a coarse root filter that
approximately covers an entire object and higher resolu-
tion part filters that cover smaller parts of the object.
Figure 3 illustrates an instantiation of such a model
in a feature pyramid. The root filter location defines a
detection window (the pixels contributing to the part of
the feature map covered by the filter). The part filters
are placed λ levels down in the pyramid, so the features
at that level are computed at twice the resolution of the
features in the root filter level.
We have found that using higher resolution features
for defining part filters is essential for obtaining high
recognition performance. With this approach the part
filters capture finer resolution features that are localized
to greater accuracy when compared to the features cap-
tured by the root filter. Consider building a model for a
face. The root filter could capture coarse resolution edges
such as the face boundary while the part filters could
capture details such as eyes, nose and mouth.
A model for an object with n parts is formally defined
by a (n + 2)-tuple (F0, P1, . . . , Pn, b) where F0 is a root
filter, Pi is a model for the i-th part and b is a real-
valued bias term. Each part model is defined by a 3-tuple
(Fi, vi, di) where Fi is a filter for the i-th part, vi is a
two-dimensional vector specifying an “anchor” position
for part i relative to the root position, and di is a four-
dimensional vector specifying coefficients of a quadratic
function defining a deformation cost for each possible
placement of the part relative to the anchor position.
An object hypothesis specifies the location of each
filter in the model in a feature pyramid, z = (p0, . . . , pn),
where pi = (xi, yi, li) specifies the level and position of
the i-th filter. We require that the level of each part is
such that the feature map at that level was computed at
twice the resolution of the root level, li = l0− λ for i > 0.
The score of a hypothesis is given by the scores of each
filter at their respective locations (the data term) minus
a deformation cost that depends on the relative position
of each part with respect to the root (the spatial prior),

6
plus the bias,
score(p0, . . . , pn) =
n∑
i=0
F′
i· φ(H, pi)−
n∑
i=1
di· φd(dxi, dyi) + b, (2)
where
(dxi, dyi) = (xi, yi)− (2(x0, y0) + vi) (3)
gives the displacement of the i-th part relative to its
anchor position and
φd(dx, dy) = (dx, dy, dx2, dy2) (4)
are deformation features.
Note that if di = (0 , 0, 1, 1) the deformation cost for
the i-th part is the squared distance between its actual
position and its anchor position relative to the root. In
general the deformation cost is an arbitrary separable
quadratic function of the displacements.
The bias term is introduced in the score to make the
scores of multiple models comparable when we combine
them into a mixture model.
The score of a hypothesis z can be expressed in terms
of a dot product, β· ψ(H, z), between a vector of model
parameters β and a vector ψ(H, z),
β = (F′
0, . . . , F′
n, d1, . . . , dn, b). (5)
ψ(H, z) = (φ(H, p0), . . . φ(H, pn),
−φd(dx1, dy1), . . . ,−φd(dxn, dyn), 1). (6)
This illustrates a connection between our models and
linear classifiers. We use this relationship for learning
the model parameters with the latent SVM framework.
3.2 Matching
To detect objects in an image we compute an overall
score for each root location according to the best possible
placement of the parts,
score(p0) = max
p1,...,pn
score(p0, . . . , pn). (7)
High-scoring root locations define detections while the
locations of the parts that yield a high-scoring root
location define a full object hypothesis.
By defining an overall score for each root location we
can detect multiple instances of an object (we assume
there is at most one instance per root location). This
approach is related to sliding-window detectors because
we can think of score(p0) as a score for the detection
window specified by the root filter.
We use dynamic programming and generalized dis-
tance transforms (min-convolutions) [14], [15] to com-
pute the best locations for the parts as a function of
the root location. The resulting method is very efficient,
taking O(nk) time once filter responses are computed,
where n is the number of parts in the model and k is
the total number of locations in the feature pyramid. We
briefly describe the method here and refer the reader to
[14], [15] for more details.
Let Ri,l(x, y) = F′
i· φ(H, (x, y, l)) be an array storing
the response of the i-th model filter in the l-th level
of the feature pyramid. The matching algorithm starts
by computing these responses. Note that Ri,l is a cross-
correlation between Fi and level l of the feature pyramid.
After computing filter responses we transform the re-
sponses of the part filters to allow for spatial uncertainty,
Di,l(x, y) = max
dx,dy
(Ri,l(x + dx, y + dy)− di· φd(dx, dy)) .
(8)
This transformation spreads high filter scores to nearby
locations, taking into account the deformation costs. The
value Di,l(x, y) is the maximum contribution of the i-th
part to the score of a root location that places the anchor
of this part at position (x, y) in level l.
The transformed array, Di,l, can be computed in linear
time from the response array, Ri,l, using the generalized
distance transform algorithm from [14].
The overall root scores at each level can be expressed
by the sum of the root filter response at that level, plus
shifted versions of transformed and subsampled part
responses,
score(x0, y0, l0) =
R0,l0(x0, y0) +
n∑
i=1
Di,l0−λ(2(x0, y0) + vi) + b. (9)
Recall that λ is the number of levels we need to go down
in the feature pyramid to get to a feature map that was
computed at exactly twice the resolution of another one.
Figure 4 illustrates the matching process.
To understand equation (9) note that for a fixed root
location we can independently pick the best location for
each part because there are no interactions among parts
in the score of a hypothesis. The transformed arrays Di,l
give the contribution of the i-th part to the overall root
score, as a function of the anchor position for the part. So
we obtain the total score of a root position at level l by
adding up the root filter response and the contributions
from each part, which are precomputed in Di,l−λ.
In addition to computing Di,l the algorithm from [14]
can also compute optimal displacements for a part as a
function of its anchor position,
Pi,l(x, y) = argmax
dx,dy
(Ri,l(x + dx, y + dy)− di· φd(dx, dy)) .
(10)
After finding a root location (x0, y0, l0) with high score
we can find the corresponding part locations by looking
up the optimal displacements in Pi,l0−λ(2(x0, y0) + vi).
3.3 Mixture Models
A mixture model with m components is defined by a
m-tuple, M = (M1, . . . , Mm), where Mc is the model for
the c-th component.
An object hypothesis for a mixture model specifies a
mixture component, 1≤ c≤ m, and a location for each

7
+
x
x
x
...
...
...
model
response of root filter
transformed responses
response of part filters
feature map feature map at twice the resolution
combined score of 
root locations
low value high value
color encoding of filter 
response values
Fig. 4. The matching process at one scale. Responses from the root and part filters are computed a different
resolutions in the feature pyramid. The transformed responses are combined to yield a final score for each root
location. We show the responses and transformed responses for the “head” and “right shoulder” parts. Note how the
“head” filter is more discriminative. The combined scores clearly show two good hypothesis for the object at this scale.

8
filter of Mc, z = ( c, p0, . . . , pnc). Here nc is the number
of parts in Mc. The score of this hypothesis is the score
of the hypothesis z′ = ( p0, . . . , pnc) for the c-th model
component.
As in the case of a single component model the score
of a hypothesis for a mixture model can be expressed
by a dot product between a vector of model parameters
β and a vector ψ(H, z). For a mixture model the vector
β is the concatenation of the model parameter vectors
for each component. The vector ψ(H, z) is sparse, with
non-zero entries defined by ψ(H, z′) in a single interval
matching the interval of βc in β,
β = (β1, . . . , βm). (11)
ψ(H, z) = (0, . . . ,0, ψ(H, z′), 0, . . . ,0). (12)
With this construction β· ψ(H, z) = βc· ψ(H, z′).
To detect objects using a mixture model we use the
matching algorithm described above to find root loca-
tions that yield high scoring hypotheses independently
for each component.
4 L ATENT SVM
Consider a classifier that scores an example x with a
function of the form,
fβ(x) = max
z∈Z(x)
β· Φ(x, z). (13)
Here β is a vector of model parameters and z are latent
values. The set Z(x) defines the possible latent values
for an example x. A binary label for x can be obtained
by thresholding its score.
In analogy to classical SVMs we train β from labeled
examples D = (⟨x1, y1⟩, . . .,⟨xn, yn⟩), where yi∈{− 1, 1},
by minimizing the objective function,
LD(β) = 1
2||β||2 + C
n∑
i=1
max(0, 1− yifβ(xi)), (14)
where max(0, 1− yifβ(xi)) is the standard hinge loss
and the constant C controls the relative weight of the
regularization term.
Note that if there is a single possible latent value for
each example (|Z(xi)| = 1) then fβ is linear in β, and we
obtain linear SVMs as a special case of latent SVMs.
4.1 Semi-convexity
A latent SVM leads to a non-convex optimization prob-
lem. However, a latent SVM is semi-convex in the sense
described below, and the training problem becomes con-
vex once latent information is specified for the positive
training examples.
Recall that the maximum of a set of convex functions
is convex. In a linear SVM we have that fβ(x) = β· Φ(x)
is linear in β. In this case the hinge loss is convex for
each example because it is always the maximum of two
convex functions.
Note that fβ(x) as defined in (13) is a maximum of
functions each of which is linear in β. Hence fβ(x) is
convex in β and thus the hinge loss, max(0, 1− yifβ(xi)),
is convex in β when yi =−1. That is, the loss function is
convex in β for negative examples. We call this property
of the loss function semi-convexity.
In a general latent SVM the hinge loss is not convex for
a positive example because it is the maximum of a con-
vex function (zero) and a concave function ( 1−yifβ(xi)).
Now consider a latent SVM where there is a single
possible latent value for each positive example. In this
case fβ(xi) is linear for a positive example and the loss
due to each positive is convex. Combined with the semi-
convexity property, (14) becomes convex.
4.2 Optimization
Let Zp specify a latent value for each positive example
in a training set D. We can define an auxiliary objective
function LD(β, Zp) = LD(Zp)(β), where D(Zp) is derived
from D by restricting the latent values for the positive
examples according to Zp. That is, for a positive example
we set Z(xi) ={zi} where zi is the latent value specified
for xi by Zp. Note that
LD(β) = min
Zp
LD(β, Zp). (15)
In particular LD(β)≤ LD(β, Zp). The auxiliary objective
function bounds the LSVM objective. This justifies train-
ing a latent SVM by minimizing LD(β, Zp).
In practice we minimize LD(β, Zp) using a “coordinate
descent” approach:
1) Relabel positive examples: Optimize LD(β, Zp) over
Zp by selecting the highest scoring latent value for
each positive example,
zi = argmaxz∈Z(xi) β· Φ(xi, z).
2) Optimize beta: Optimize LD(β, Zp) over β by solv-
ing the convex optimization problem defined by
LD(Zp)(β).
Both steps always improve or maintain the value of
LD(β, Zp). After convergence we have a relatively strong
local optimum in the sense that step 1 searches over
an exponentially-large space of latent values for positive
examples while step 2 searches over all possible models,
implicitly considering the exponentially-large space of
latent values for all negative examples.
We note, however, that careful initialization of β may
be necessary because otherwise we may select unreason-
able latent values for the positive examples in step 1, and
this could lead to a bad model.
The semi-convexity property is important because it
leads to a convex optimization problem in step 2, even
though the latent values for the negative examples are
not fixed. A similar procedure that fixes latent values
for all examples in each round would likely fail to yield
good results. Suppose we let Z specify latent values for
all examples in D. Since LD(β) effectively maximizes
over negative latent values, LD(β) could be much larger
than LD(β, Z), and we should not expect that minimiz-
ing LD(β, Z) would lead to a good model.

9
4.3 Stochastic gradient descent
Step 2 ( Optimize Beta) of the coordinate descent method
can be solved via quadratic programming [3]. It can
also be solved via stochastic gradient descent. Here we
describe a gradient descent approach for optimizing β
over an arbitrary training set D. In practice we use a
modified version of this procedure that works with a
cache of feature vectors for D(Zp) (see Section 4.5).
Let zi(β) = argmaxz∈Z(xi) β· Φ(xi, z).
Then fβ(xi) = β· Φ(xi, zi(β)).
We can compute a sub-gradient of the LSVM objective
function as follows,
∇LD(β) = β + C
n∑
i=1
h(β, xi, yi) (16)
h(β, xi, yi) =
{ 0 if yifβ(xi)≥ 1
−yiΦ(xi, zi(β)) otherwise (17)
In stochastic gradient descent we approximate ∇LD
using a subset of the examples and take a step in
its negative direction. Using a single example, ⟨xi, yi⟩,
we approximate ∑n
i=1 h(β, xi, yi) with nh(β, xi, yi). The
resulting algorithm repeatedly updates β as follows:
1) Let αt be the learning rate for iteration t.
2) Let i be a random example.
3) Let zi = argmaxz∈Z(xi) β· Φ(xi, z).
4) If yifβ(xi) = yi(β· Φ(xi, zi))≥ 1 set β := β− αtβ.
5) Else set β := β− αt(β− CnyiΦ(xi, zi)).
As in gradient descent methods for linear SVMs we
obtain a procedure that is quite similar to the perceptron
algorithm. If fβ correctly classifies the random example
xi (beyond the margin) we simply shrink β. Otherwise
we shrink β and add a scalar multiple of Φ(xi, zi) to it.
For linear SVMs a learning rate αt = 1 /t has been
shown to work well [37]. However, the time for con-
vergence depends on the number of training examples,
which for us can be very large. In particular, if there
are many “easy” examples, step 2 will often pick one of
these and we do not make much progress.
4.4 Data-mining hard examples, SVM version
When training a model for object detection we often
have a very large number of negative examples (a single
image can yield 105 examples for a scanning window
classifier). This can make it infeasible to consider all
negative examples simultaneously. Instead, it is common
to construct training data consisting of the positive in-
stances and “hard negative” instances.
Bootstrapping methods train a model with an initial
subset of negative examples, and then collect negative
examples that are incorrectly classified by this initial
model to form a set of hard negatives. A new model is
trained with the hard negative examples and the process
may be repeated a few times.
Here we describe a data-mining algorithm motivated
by the bootstrapping idea for training a classical (non-
latent) SVM. The method solves a sequence of training
problems using a relatively small number of hard exam-
ples and converges to the exact solution of the training
problem defined by a large training set. This requires a
margin-sensitive definition of hard examples.
We define hard and easy instances of a training set D
relative to β as follows,
H(β, D) ={⟨x, y⟩∈ D| yfβ(x) < 1}. (18)
E(β, D) ={⟨x, y⟩∈ D| yfβ(x) > 1}. (19)
That is, H(β, D) are the examples in D that are incor-
rectly classified or inside the margin of the classifier
defined by β. Similarly E(β, D) are the examples in
D that are correctly classified and outside the margin.
Examples on the margin are neither hard nor easy.
Let β∗(D) = argminβ LD(β).
Since LD is strictly convex β∗(D) is unique.
Given a large training set D we would like to find a
small set of examples C⊆ D such that β∗(C) = β∗(D).
Our method starts with an initial “cache” of examples
and alternates between training a model and updating
the cache. In each iteration we remove easy examples
from the cache and add new hard examples. A special
case involves keeping all positive examples in the cache
and data-mining over negatives.
Let C1 ⊆ D be an initial cache of examples. The
algorithm repeatedly trains a model and updates the
cache as follows:
1) Let βt := β∗(Ct) (train a model using Ct).
2) If H(βt, D)⊆ Ct stop and return βt.
3) Let C′
t := Ct\X for any X such that X⊆ E(βt, Ct)
(shrink the cache).
4) Let Ct+1 := C′
t∪ X for any X such that X⊆ D and
X∩ H(βt, D)\Ct̸=∅ (grow the cache).
In step 3 we shrink the cache by removing examples
from Ct that are outside the margin defined by βt. In
step 4 we grow the cache by adding examples from
D, including at least one new example that is inside
the margin defined by βt. Such example must exist
otherwise we would have returned in step 2.
The following theorem shows that when we stop we
have found β∗(D).
Theorem 1: Let C⊆ D and β = β∗(C). If H(β, D)⊆ C
then β = β∗(D).
Proof: C ⊆ D implies LD(β∗(D))≥ LC(β∗(C)) =
LC(β). Since H(β, D) ⊆ C all examples in D\C have
zero loss on β. This implies LC(β) = LD(β). We conclude
LD(β∗(D)) ≥ LD(β), and because LD has a unique
minimum β = β∗(D).
The next result shows the algorithm will stop after a
finite number of iterations. Intuitively this follows from
the fact that LCt(β∗(Ct)) grows in each iteration, but it
is bounded by LD(β∗(D)).
Theorem 2: The data-mining algorithm terminates.
Proof: When we shrink the cache C′
t contains all
examples from Ct with non-zero loss in a ball around
βt. This implies LC′
t is identical to LCt in a ball around

10
βt, and since βt is a minimum of LCt it also must be a
minimum of LC′
t. Thus LC′
t(β∗(C′
t)) = LCt(β∗(Ct)).
When we grow the cache Ct+1\C′
t contains at least one
example⟨x, y⟩ with non-zero loss at βt. Since C′
t⊆ Ct+1
we have LCt+1(β) ≥ LC′
t(β) for all β. If β∗(Ct+1) ̸=
β∗(C′
t) then LCt+1(β∗(Ct+1)) > LC′
t(β∗(C′
t)) because LC′
t
has a unique minimum. If β∗(Ct+1) = β∗(C′
t) then
LCt+1(β∗(Ct+1)) > LC′
t(β∗(C′
t)) due to⟨x, y⟩.
We conclude LCt+1(β∗(Ct+1)) > L Ct(β∗(Ct)). Since
there are finitely many caches the loss in the cache can
only grow a finite number of times.
4.5 Data-mining hard examples, LSVM version
Now we describe a data-mining algorithm for training a
latent SVM when the latent values for the positive examples
are fixed. That is, we are optimizing LD(Zp)(β), and not
LD(β). As discussed above this restriction ensures the
optimization problem is convex.
For a latent SVM instead of keeping a cache of exam-
ples x, we keep a cache of (x, z) pairs where z∈ Z(x).
This makes it possible to avoid doing inference over all
of Z(x) in the inner loop of an optimization algorithm
such as gradient descent. Moreover, in practice we can
keep a cache of feature vectors, Φ(x, z), instead of (x, z)
pairs. This representation is simpler (its application in-
dependent) and can be much more compact.
A feature vector cache F is a set of pairs (i, v) where
1≤ i≤ n is the index of an example and v = Φ(xi, z) for
some z∈ Z(xi). Note that we may have several pairs
(i, v)∈ F for each example xi. If the training set has
fixed labels for positive examples this may still be true
for the negative examples.
Let I(F ) be the examples indexed by F . The feature
vectors in F define an objective function for β, where we
only consider examples indexed by I(F ), and for each
example we only consider feature vectors in the cache,
LF (β) = 1
2||β||2+C
∑
i∈I(F )
max(0, 1−yi( max
(i,v)∈F
β·v)). (20)
We can optimize LF via gradient descent by modi-
fying the method in Section 4.3. Let V (i) be the set of
feature vectors v such that (i, v)∈ F . Then each gradient
descent iteration simplifies to:
1) Let αt be the learning rate for iteration t.
2) Let i∈ I(F ) be a random example indexed by F .
3) Let vi = argmaxv∈V (i) β· v.
4) If yi(β· vi)≥ 1 set β = β− αtβ.
5) Else set β = β− αt(β− Cnyivi).
Now the size of I(F ) controls the number of iterations
necessary for convergence, while the size of V (i) controls
the time it takes to execute step 3. In step 5 n =|I(F )|.
Let β∗(F ) = argminβ LF (β).
We would like to find a small cache for D(Zp) with
β∗(F ) = β∗(D(Zp)).
We define the hard feature vectors of a training set D
relative to β as,
H(β, D) ={(i, Φ(xi, zi))|
zi = argmax
z∈Z(xi)
β· Φ(xi, z) and yi(β· Φ(xi, zi)) < 1}. (21)
That is, H(β, D) are pairs (i, v) where v is the highest
scoring feature vector from an example xi that is inside
the margin of the classifier defined by β.
We define the easy feature vectors in a cache F as
E(β, F ) ={(i, v)∈ F| yi(β· v) > 1} (22)
These are the feature vectors from F that are outside the
margin defined by β.
Note that if yi(β· v)≤ 1 then (i, v) is not considered
easy even if there is another feature vector for the i-th
example in the cache with higher score than v under β.
Now we describe the data-mining algorithm for com-
puting β∗(D(Zp)).
The algorithm works with a cache of feature vectors
for D(Zp). It alternates between training a model and
updating the cache.
Let F1 be an initial cache of feature vectors. Now
consider the following iterative algorithm:
1) Let βt := β∗(Ft) (train a model).
2) If H(β, D(Zp))⊆ Ft stop and return βt.
3) Let F′
t := Ft\X for any X such that X⊆ E(βt, Ft)
(shrink the cache).
4) Let Ft+1 := F′
t∪ X for any X such that
X∩ H(βt, D(Zp))\Ft̸=∅ (grow the cache).
Sstep 3 shrinks the cache by removing easy feature
vetors. Step 4 grows the cache by adding “new” feature
vectors, including at least one from H(βt, D(Zp)). Note
that over time we will accumulate multiple feature vec-
tors from the same negative example in the cache.
We can show this algorithm will eventually stop and
return β∗(D(Zp)). This follows from arguments analo-
gous to the ones used in Section 4.4.
5 T RAINING MODELS
Now we consider the problem of training models from
images labeled with bounding boxes around objects of
interest. This is the type of data available in the PASCAL
datasets. Each dataset contains thousands of images and
each image has annotations specifying a bounding box
and a class label for each target object present in the
image. Note that this is a weakly labeled setting since
the bounding boxes do not specify component labels or
part locations.
We describe a procedure for initializing the structure
of a mixture model and learning all parameters. Pa-
rameter learning is done by constructing a latent SVM
training problem. We train the latent SVM using the
coordinate descent approach described in Section 4.2
together with the data-mining and gradient descent
algorithms that work with a cache of feature vectors

11
from Section 4.5. Since the coordinate descent method is
susceptible to local minima we must take care to ensure
a good initialization of the model.
5.1 Learning parameters
Let c be an object class. We assume the training examples
for c are given by positive bounding boxes P and a set
of background images N. P is a set of pairs (I, B) where
I is an image and B is a bounding box for an object of
class c in I.
Let M be a (mixture) model with fixed structure. Recall
that the parameters for a model are defined by a vector
β. To learn β we define a latent SVM training problem
with an implicitly defined training set D, with positive
examples from P , and negative examples from N.
Each example⟨x, y⟩∈ D has an associated image and
feature pyramid H(x). Latent values z∈ Z(x) specify an
instantiation of M in the feature pyramid H(x).
Now define Φ(x, z) = ψ(H(x), z). Then β· Φ(x, z) is
exactly the score of the hypothesis z for M on H(x).
A positive bounding box (I, B)∈ P specifies that the
object detector should “fire” in a location defined by B.
This means the overall score (7) of a root location defined
by B should be high.
For each (I, B)∈ P we define a positive example x
for the LSVM training problem. We define Z(x) so the
detection window of a root filter specified by a hypoth-
esis z ∈ Z(x) overlaps with B by at least 50%. There
are usually many root locations, including at different
scales, that define detection windows with 50% overlap.
We have found that treating the root location as a latent
variable is helpful to compensate for noisy bounding box
labels in P . A similar idea was used in [40].
Now consider a background image I∈ N. We do not
want the object detector to “fire” in any location of the
feature pyramid for I. This means the overall score (7) of
every root location should be low. LetG be a dense set of
locations in the feature pyramid. We define a different
negative example x for each location (i, j, l) ∈ G. We
define Z(x) so the level of the root filter specified by
z∈ Z(x) is l, and the center of its detection window is
(i, j). Note that there is a very large number of negative
examples obtained from each image. This is consistent
with the requirement that a scanning window classifier
should have low false positive rate.
The procedure Train is outlined below. The outer-
most loop implements a fixed number of iterations of
coordinate descent on LD(β, Zp). Lines 3-6 implement
the Relabel positives step. The resulting feature vectors,
one per positive example, are stored in Fp. Lines 7-14
implement the Optimize beta step. Since the number of
negative examples implicitly defined by N is very large
we use the LSVM data-mining algorithm. We iterate
data-mining a fixed number of times rather than until
convergence for practical reasons. At each iteration we
collect hard negative examples in Fn, train a new model
using gradient descent, and then shrink Fn by removing
easy feature vectors. During data-mining we grow the
cache by iterating over the images in N sequentially,
until we reach a memory limit.
Data:
Positive examples P ={(I1, B1), . . . ,(In, Bn)}
Negative images N ={J1, . . . , Jm}
Initial model β
Result: New model β
Fn :=∅1
for relabel := 1 to num-relabel do2
Fp :=∅3
for i := 1 to n do4
Add detect-best(β,Ii,Bi) to Fp5
end6
for datamine := 1 to num-datamine do7
for j := 1 to m do8
if|Fn|≥ memory-limit then break9
Add detect-all(β,Jj,−(1 + δ)) to Fn10
end11
β :=gradient-descent(Fp∪ Fn)12
Remove (i, v) with β· v <−(1 + δ) from Fn13
end14
end15
Procedure Train
The function detect-best(β, I, B) finds the highest
scoring object hypothesis with a root filter that signifi-
cantly overlaps B in I. The function detect-all(β, I, t)
computes the best object hypothesis for each root lo-
cation and selects the ones that score above t. Both of
these functions can be implemented using the matching
procedure in Section 3.2.
The function gradient-descent(F ) trains β using
feature vectors in the cache as described in Section 4.5.
In practice we modified the algorithm to constrain the
coefficients of the quadratic terms in the deformation
models to be above 0.01. This ensures the deformation
costs are convex, and not “too flat”. We also constrain
the model to be symmetric along the vertical axis. Filters
that are positioned along the center vertical axis of the
model are constrained to 

[... truncated for benchmark fixture size — see script body_max_chars ...]


## References

[1] Y. Amit and A. Kong, “Graphical templates for model registra-
tion,” IEEE Transactions on Pattern Analysis and Machine Intelligence,
vol. 18, no. 3, pp. 225–236, 1996.
[2] Y. Amit and A. Trouve, “POP: Patchwork of parts models for
object recognition,” International Journal of Computer Vision, vol. 75,
no. 2, pp. 267–282, 2007.
[3] S. Andrews, I. Tsochantaridis, and T. Hofmann, “Support vector
machines for multiple-instance learning,” in Advances in Neural
Information Processing Systems , 2003.
[4] A. Bar-Hillel and D. Weinshall, “Efficient learning of relational ob-
ject class models,” International Journal of Computer Vision , vol. 77,
no. 1, pp. 175–198, 2008.
[5] E. Bernstein and Y. Amit, “Part-based statistical models for object
classification and detection,” in IEEE Conference on Computer Vision
and Pattern Recognition , 2005.
[6] M. Burl, M. Weber, and P . Perona, “A probabilistic approach to
object recognition using local photometry and global geometry,”
in European Conference on Computer Vision , 1998.
[7] T. Cootes, G. Edwards, and C. Taylor, “Active appearance mod-
els,” IEEE Transactions on Pattern Analysis and Machine Intelligence ,
vol. 23, no. 6, pp. 681–685, 2001.
[8] J. Coughlan, A. Yuille, C. English, and D. Snow, “Efficient de-
formable template detection and localization without user initial-
ization,” Computer Vision and Image Understanding , vol. 78, no. 3,
pp. 303–319, June 2000.
[9] D. Crandall, P . Felzenszwalb, and D. Huttenlocher, “Spatial pri-
ors for part-based recognition using statistical models,” in IEEE
Conference on Computer Vision and Pattern Recognition , 2005.
[10] N. Dalal and B. Triggs, “Histograms of oriented gradients for
human detection,” in IEEE Conference on Computer Vision and
Pattern Recognition, 2005.
[11] M. Everingham, L. Van Gool, C. K. I. Williams, J. Winn, and
A. Zisserman, “The PASCAL Visual Object Classes Challenge 2007
(VOC2007) Results.” [Online]. Available: http://www.pascal-
network.org/challenges/VOC/voc2007/
[12] ——, “The PASCAL Visual Object Classes Challenge 2008
(VOC2008) Results.” [Online]. Available: http://www.pascal-
network.org/challenges/VOC/voc2008/
[13] M. Everingham, A. Zisserman, C. K. I. Williams, and
L. Van Gool, “The PASCAL Visual Object Classes Challenge 2006
(VOC2006) Results.” [Online]. Available: http://www.pascal-
network.org/challenges/VOC/voc2006/
[14] P . Felzenszwalb and D. Huttenlocher, “Distance transforms of
sampled functions,” Cornell University CIS, Tech. Rep. 2004-1963,
2004.
[15] ——, “Pictorial structures for object recognition,” International
Journal of Computer Vision , vol. 61, no. 1, 2005.
[16] P . Felzenszwalb and D. McAllester, “The generalized A* architec-
ture,” Journal of Artificial Intelligence Research , vol. 29, pp. 153–190,
2007.
[17] P . Felzenszwalb, D. McAllester, and D. Ramanan, “A discrim-
inatively trained, multiscale, deformable part model,” in IEEE
Conference on Computer Vision and Pattern Recognition , 2008.
[18] R. Fergus, P . Perona, and A. Zisserman, “Object class recognition
by unsupervised scale-invariant learning,” in IEEE Conference on
Computer Vision and Pattern Recognition , 2003.
[19] ——, “A sparse object category model for efficient learning and
exhaustive recognition,” in IEEE Conference on Computer Vision and
Pattern Recognition, 2005.
[20] M. Fischler and R. Elschlager, “The representation and matching
of pictorial structures,” IEEE Transactions on Computer , vol. 22,
no. 1, 1973.
[21] U. Grenander, Y. Chow, and D. Keenan, HANDS: A Pattern-
Theoretic Study of Biological Shapes . Springer-Verlag, 1991.
[22] D. Hoiem, A. Efros, and M. Hebert, “Putting objects in per-
spective,” International Journal of Computer Vision , vol. 80, no. 1,
October 2008.
[23] A. Holub and P . Perona, “A discriminative framework for mod-

20
elling object classes,” in IEEE Conference on Computer Vision and
Pattern Recognition, 2005.
[24] Y. Jin and S. Geman, “Context and hierarchy in a probabilistic
image model,” in IEEE Conference on Computer Vision and Pattern
Recognition, 2006.
[25] T. Joachims, “Making large-scale svm learning practical,” in Ad-
vances in Kernel Methods - Support Vector Learning , B. Sch ̈olkopf,
C. Burges, and A. Smola, Eds. MIT Press, 1999.
[26] Y. Ke and R. Sukthankar, “PCA-SIFT: A more distinctive represen-
tation for local image descriptors,” in IEEE Conference on Computer
Vision and Pattern Recognition , 2004.
[27] Y. LeCun, S. Chopra, R. Hadsell, R. Marc’Aurelio, and F. Huang,
“A tutorial on energy-based learning,” in Predicting Structured
Data, G. Bakir, T. Hofman, B. Sch ̈olkopf, A. Smola, and B. Taskar,
Eds. MIT Press, 2006.
[28] B. Leibe, A. Leonardis, and B. Schiele, “Robust object detection
with interleaved categorization and segmentation,” International
Journal of Computer Vision , vol. 77, no. 1, pp. 259–289, 2008.
[29] D. Lowe, “Distinctive image features from scale-invariant key-
points,” International Journal of Computer Vision , vol. 60, no. 2, pp.
91–110, November 2004.
[30] C. Papageorgiou, M. Oren, and T. Poggio, “A general framework
for object detection,” in IEEE International Conference on Computer
Vision, 1998.
[31] W. Plantinga and C. Dyer, “An algorithm for constructing the
aspect graph,” in Foundations of Computer Science, 1985., 27th
Annual Symposium on , 1986, pp. 123–131.
[32] A. Quattoni, S. Wang, L. Morency, M. Collins, and T. Darrell,
“Hidden conditional random fields,” IEEE Transactions on Pattern
Analysis and Machine Intelligence , vol. 29, no. 10, pp. 1848–1852,
October 2007.
[33] A. Rabinovich, A. Vedaldi, C. Galleguillos, E. Wiewiora, and
S. Belongie, “Objects in context,” in IEEE International Conference
on Computer Vision , 2007.
[34] D. Ramanan and C. Sminchisescu, “Training deformable models
for localization,” in IEEE Conference on Computer Vision and Pattern
Recognition, 2006.
[35] H. Rowley, S. Baluja, and T. Kanade, “Human face detection in
visual scenes,” Carnegie Mellon University, Tech. Rep. CMU-CS-
95-158R, 1995.
[36] H. Schneiderman and T. Kanade, “A statistical method for 3d
object detection applied to faces and cars,” in IEEE Conference on
Computer Vision and Pattern Recognition , 2000.
[37] S. Shalev-Shwartz, Y. Singer, and N. Srebro, “Pegasos: Primal
estimated sub-gradient solver for SVM,” in International Conference
on Machine Learning , 2007.
[38] K. Sung and T. Poggio, “Example-based learning for view-based
human face detection,” Massachussets Institute of Technology,
Tech. Rep. A.I. Memo No. 1521, 1994.
[39] A. Torralba, “Contextual priming for object detection,” Interna-
tional Journal of Computer Vision , vol. 53, no. 2, pp. 169–191, July
2003.
[40] P . Viola, J. Platt, and C. Zhang, “Multiple instance boosting for
object detection,” in Advances in Neural Information Processing
Systems, 2005.
[41] P . Viola and M. Jones, “Robust real-time face detection,” Interna-
tional Journal of Computer Vision , vol. 57, no. 2, pp. 137–154, May
2004.
[42] M. Weber, M. Welling, and P . Perona, “Towards automatic discov-
ery of object categories,” in IEEE Conference on Computer Vision and
Pattern Recognition, 2000.
[43] A. Yuille, P . Hallinan, and D. Cohen, “Feature extraction from
faces using deformable templates,” International Journal of Com-
puter Vision, vol. 8, no. 2, pp. 99–111, 1992.
[44] J. Zhang, M. Marszalek, S. Lazebnik, and C. Schmid, “Local fea-
tures and kernels for classification of texture and object categories:
A comprehensive study,” International Journal of Computer Vision ,
vol. 73, no. 2, pp. 213–238, June 2007.
[45] S. Zhu and D. Mumford, “A stochastic grammar of images,”
Foundations and Trends in Computer Graphics and Vision, vol. 2, no. 4,
pp. 259–362, 2007.