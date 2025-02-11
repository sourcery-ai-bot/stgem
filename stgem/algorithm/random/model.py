import numpy as np

from stgem.algorithm import Model, ModelSkeleton

class Random_Model(Model):

    def skeletonize(self):
        return Random_ModelSkeleton(self.parameters)

    @classmethod
    def setup_from_skeleton(cls, skeleton, search_space, device, logger=None, use_previous_rng=False):
        model = cls(skeleton.parameters)
        model.setup(search_space, device, logger, use_previous_rng)

        return model

class Random_ModelSkeleton(ModelSkeleton):

    def __init__(self, parameters):
        super().__init__(parameters)

        self.random_func = lambda: np.random.uniform(-1, 1, size=self.input_dimension)

    def _generate_test(self, N=1, random_func=None):
        result = np.empty(shape=(N, self.input_dimension))
        for i in range(N):
            result[i,:] = random_func()

        return result

    def generate_test(self, N=1):
        return self._generate_test(N, self.random_func)

    def predict_objective(self, test):
        return 1

class Uniform(Random_Model,Random_ModelSkeleton):
    """Implements a random test model which directly uses the sampling provided by
    the SUT."""

    default_parameters = {"min_distance": 0.0}

    def __init__(self, parameters=None):
        Model.__init__(self, parameters)
        Random_ModelSkeleton.__init__(self, parameters)

    def setup(self, search_space, device, logger=None, use_previous_rng=False):
        super().setup(search_space, device, logger, use_previous_rng)

        if self.min_distance < 0:
            raise Exception("Random search minimum distance must be nonnegative.")

        if self.min_distance > 0:
            # If all used points were stored in a Numpy array, we could use
            # faster Numpy operations on it, but then array growing is an
            # issue. Since we are not likely to have more than some hundreds
            # of tests, using Python arrays is reasonably fast.
            self.used_points = []

    def _satisfies_min_distance(self, test):
        return all(
            np.linalg.norm(p - test) >= self.min_distance for p in self.used_points
        )

    def generate_test(self, N=1):
        result = np.empty(shape=(N, self.input_dimension))
        c = 0
        while c < N:
            test = self.search_space.sample_input_space()
            if self.min_distance == 0 or self._satisfies_min_distance(test):
                result[c,:] = test
                c += 1

                if self.min_distance > 0:
                    self.used_points.append(test.reshape(-1))

        return result

class Halton(Random_Model,Random_ModelSkeleton):
    """Random sampling using a Halton sequence."""

    def __init__(self, parameters=None):
        Model.__init__(self, parameters)
        Random_ModelSkeleton.__init__(self, parameters)

    def setup(self, search_space, device, logger, use_previous_rng=False):
        super().setup(search_space, device, logger)

        # Save current RNG state and use previous.
        if use_previous_rng:
            # Simply reset the sampler.
            self.hal.reset()
        else:
            # Get a random seed using the search space RNG.
            seed = int(self.search_space.rng.uniform() * 2**32)

            from scipy.stats import qmc

            self.hal = qmc.Halton(d=self.search_space.input_dimension, scramble=True, seed=seed)

        self.random_func = lambda: 2*self.hal.random().reshape(-1) - 1

class LHS(Random_Model,Random_ModelSkeleton):
    """Implements a random test model based on Latin hypercube design."""

    def __init__(self, parameters=None):
        Model.__init__(self, parameters)
        Random_ModelSkeleton.__init__(self, parameters)

    def setup(self, search_space, device, logger=None, use_previous_rng=False):
        super().setup(search_space, device, logger, use_previous_rng)

        if "samples" not in self.parameters:
            raise Exception("The 'samples' key must be provided for the algorithm for determining random sample size.")

        # Save current RNG state and use previous.
        if use_previous_rng:
            current_rng_state = self.search_space.rng.get_state()
            self.search_space.rng.set_state(self.previous_rng_state["numpy"])
        else:
            self.previous_rng_state = {}
            self.previous_rng_state["numpy"] = self.search_space.rng.get_state()

        # Create the design immediately.
        self.random_tests = 2*(self.lhs(self.search_space.input_dimension, samples=self.samples) - 0.5)

        self.current = -1

        # Restore RNG state.
        if use_previous_rng:
            self.search_space.rng.set_state(current_rng_state)

        def random_func(self):
            self.current += 1

            if self.current >= len(self.random_tests):
                raise Exception("Random sample exhausted.")

            return self.random_tests[self.current]

        self.random_func = lambda: random_func(self)

    def lhs(self, n, samples=None, criterion=None, iterations=None):
        """
        :meta private:
        Generate a latin-hypercube design.
        
        Args:
            n (int): The number of factors to generate samples for.
            samples (int, optional): The number of samples to generate for each factor. Defaults to n.
            criterion (str, optional): Allowable values are "center" or "c", "maximin" or "m",
                "centermaximin" or "cm", and "correlation" or "corr". If no value
                given, the design is simply randomized.
            iterations (int, optional): The number of iterations in the maximin
                and correlations algorithms. Defaults to 5.

        Returns:
            2d-array: An n-by-samples design matrix that has been normalized
                so factor values are uniformly spaced between zero and one.
        
        Examples:

        A 3-factor design (defaults to 3 samples)::
        
            >>> lhs(3)
            array([[ 0.40069325,  0.08118402,  0.69763298],
                   [ 0.19524568,  0.41383587,  0.29947106],
                   [ 0.85341601,  0.75460699,  0.360024  ]])
           
        A 4-factor design with 6 samples::
        
            >>> lhs(4, samples=6)
            array([[ 0.27226812,  0.02811327,  0.62792445,  0.91988196],
                   [ 0.76945538,  0.43501682,  0.01107457,  0.09583358],
                   [ 0.45702981,  0.76073773,  0.90245401,  0.18773015],
                   [ 0.99342115,  0.85814198,  0.16996665,  0.65069309],
                   [ 0.63092013,  0.22148567,  0.33616859,  0.36332478],
                   [ 0.05276917,  0.5819198 ,  0.67194243,  0.78703262]])
           
        A 2-factor design with 5 centered samples::
        
            >>> lhs(2, samples=5, criterion='center')
            array([[ 0.3,  0.5],
                   [ 0.7,  0.9],
                   [ 0.1,  0.3],
                   [ 0.9,  0.1],
                   [ 0.5,  0.7]])
           
        A 3-factor design with 4 samples where the minimum distance between
        all samples has been maximized::
        
            >>> lhs(3, samples=4, criterion='maximin')
            array([[ 0.02642564,  0.55576963,  0.50261649],
                   [ 0.51606589,  0.88933259,  0.34040838],
                   [ 0.98431735,  0.0380364 ,  0.01621717],
                   [ 0.40414671,  0.33339132,  0.84845707]])
           
        A 4-factor design with 5 samples where the samples are as uncorrelated
        as possible (within 10 iterations)::
        
            >>> lhs(4, samples=5, criterion='correlate', iterations=10)
        
        """

        """
        This code is based on
        https://github.com/tisimst/pyDOE/blob/master/pyDOE/doe_lhs.py (BSD
        licence). We needed to do the modification to support a separate numpy
        random number generator instead of the numpy global random number
        generator. This ensures deterministic design when setup with a seed.
        """

        H = None

        if samples is None:
            samples = n

        if criterion is not None:
            assert criterion.lower() in (
                'center',
                'c',
                'maximin',
                'm',
                'centermaximin',
                'cm',
                'correlation',
                'corr',
            ), f'Invalid value for "criterion": {criterion}'
        else:
            H = self._lhsclassic(n, samples)

        if criterion is None:
            criterion = 'center'

        if iterations is None:
            iterations = 5

        if H is None:
            if criterion.lower() in ('center', 'c'):
                H = _lhscentered(n, samples)
            elif criterion.lower() in ('maximin', 'm'):
                H = _lhsmaximin(n, samples, iterations, 'maximin')
            elif criterion.lower() in ('centermaximin', 'cm'):
                H = _lhsmaximin(n, samples, iterations, 'centermaximin')
            elif criterion.lower() in ('correlate', 'corr'):
                H = _lhscorrelate(n, samples, iterations)

        return H

    def _lhsclassic(self, n, samples):
        # Generate the intervals
        cut = np.linspace(0, 1, samples + 1)    
        
        # Fill points uniformly in each interval
        u = self.search_space.rng.rand(samples, n)
        a = cut[:samples]
        b = cut[1:samples + 1]
        rdpoints = np.zeros_like(u)
        for j in range(n):
            rdpoints[:, j] = u[:, j]*(b-a) + a
        
        # Make the random pairings
        H = np.zeros_like(rdpoints)
        for j in range(n):
            order = self.search_space.rng.permutation(range(samples))
            H[:, j] = rdpoints[order, j]
        
        return H
        
    def _lhscentered(n, samples):
        # Generate the intervals
        cut = np.linspace(0, 1, samples + 1)    
        
        # Fill points uniformly in each interval
        u = self.search_space.rand(samples, n)
        a = cut[:samples]
        b = cut[1:samples + 1]
        _center = (a + b)/2
        
        # Make the random pairings
        H = np.zeros_like(u)
        for j in range(n):
            H[:, j] = self.search_space.rng.permutation(_center)
        
        return H
        
    def _lhsmaximin(self, samples, iterations, lhstype):
        maxdist = 0

        # Maximize the minimum distance between points
        for _ in range(iterations):
            Hcandidate = (
                _lhsclassic(self, samples)
                if lhstype == 'maximin'
                else _lhscentered(self, samples)
            )
            d = _pdist(Hcandidate)
            if maxdist<np.min(d):
                maxdist = np.min(d)
                H = Hcandidate.copy()

        return H

    def _lhscorrelate(self, samples, iterations):
        mincorr = np.inf

        # Minimize the components correlation coefficients
        for _ in range(iterations):
            # Generate a random LHS
            Hcandidate = _lhsclassic(self, samples)
            R = np.corrcoef(Hcandidate)
            if np.max(np.abs(R[R!=1]))<mincorr:
                mincorr = np.max(np.abs(R-np.eye(R.shape[0])))
                #print('new candidate solution found with max,abs corrcoef = {}'.format(mincorr))
                H = Hcandidate.copy()

        return H
        
    def _pdist(self):
        """
        Calculate the pair-wise point distances of a matrix
        
        Parameters
        ----------
        x : 2d-array
            An m-by-n array of scalars, where there are m points in n dimensions.
        
        Returns
        -------
        d : array
            A 1-by-b array of scalars, where b = m*(m - 1)/2. This array contains
            all the pair-wise point distances, arranged in the order (1, 0), 
            (2, 0), ..., (m-1, 0), (2, 1), ..., (m-1, 1), ..., (m-1, m-2).
        
        Examples
        --------
        ::
        
            >>> x = np.array([[0.1629447, 0.8616334],
            ...               [0.5811584, 0.3826752],
            ...               [0.2270954, 0.4442068],
            ...               [0.7670017, 0.7264718],
            ...               [0.8253975, 0.1937736]])
            >>> _pdist(x)
            array([ 0.6358488,  0.4223272,  0.6189940,  0.9406808,  0.3593699,
                    0.3908118,  0.3087661,  0.6092392,  0.6486001,  0.5358894])
                  
        """
        
        self = np.atleast_2d(self)
        assert len(self.shape) == 2, 'Input array must be 2d-dimensional'

        m, n = self.shape
        if m<2:
            return []

        d = []
        for i in range(m - 1):
            d.extend(sum((self[j, :] - self[i, :])**2)**0.5 for j in range(i + 1, m))
        return np.array(d)

