import numpy as np

# TODO: Save computed robustness values for efficiency and implement reset for reuse.
# TODO: We need to check and enforce that signals have common timestamps and lengths.

class Traces:

    def __init__(self, timestamps, signals):
        self.timestamps = timestamps
        self.signals = signals

        # Check that all signals have correct length.
        for s in signals.values():
            if len(s) != len(timestamps):
                raise ValueError("All signals must have exactly as many samples as there are timestamps.")

    @classmethod
    def from_mixed_signals(C, *args, sampling_period=None):
        """Instantiate the class from signals that have different timestamps
        and different lengths. This is done by finding the maximum signal
        length and using that as a signal length, dividing this length into
        pieces according to the sampling period (smallest observed difference
        between timestamps if None), and filling values by assuming constant
        value."""

        # input: name1, timestamps1, signal1, name2, timestamps2, signal2, ...

        if sampling_period is None:
            raise NotImplementedError()

        # Maximum signal length.
        T = max(len(args[i]) for i in range(1, len(args), 3))

        # New timestamps.
        timestamps = [i*sampling_period for i in range(0, int(T/self.sampling_period) + 1)]

        # Check that all signals begin from time 0. Otherwise this does not work.

        # Fill the signals by assuming constant value.
        signals = {}
        eps = 1e-5
        for i in range(len(args), 3):
            name = args[i]
            signal_timestamps = args[i+1]
            signal_values = args[i+2]

            signals[name] = np.empty(shape=(len(timestamps)))
            pos = 0
            for t in timestamps[1:]:
                while pos < len(signal_timestamps) and signal_timestamps[pos] <= t + eps:
                    pos += 1

                value = signal_values[pos - 1]
                signals[name][pos] = value

        return C(timestamps, signals)

    def search_time_index(self, t, start=0):
        """Finds the index of the time t in the timestamps."""

        for i in range(start, len(self.timestamps)):
            if self.timestamps[i] == t:
                return i

        return -1

    def Add(self,name,signal):
        temp = {name: signal}
        self.signals.update(temp)

    def Get(self,name):
        return np.array(self.signals[name])

class STL:
    """Base class for all logical operations and atoms."""

class Signal:

    def __init__(self, name, range=None):
        self.name = name
        self.horizon = 0
        if range is not None:
            self.range = range.copy()
        else:
            self.range = None
        self.variables = [self.name]
    """
    def find_id(self,traces): 
    # from a timestamps time, return the correspondant index of the table 
        indice = -1
        for i in range(len(traces.timestamps)):
            if (traces.timestamps[i] == time):
                indice = i
        if indice == -1:
            raise Exception("time error") 
        else:
            return indice
    """
    def eval(self, traces):
        return np.array(traces.signals[self.name])

class Const:
# for a constant signal
    def __init__(self,val):
        self.nom = "Const"
        self.val = val
        self.var_range = [val,val]
        self.variables = []
        self.horizon = 0

    def eval(self, traces):
        return np.full(len(traces.timestamps), self.val)


#for the following classes there are several parameters in the initilisation :
#nom = name of the function 
#formula, right_formula, left_formula = the formulas that we use in the function
#var_range = the range of the return value
#variables = the names of the signals used in the function
#horizon = ?
#arity = number of formula that are used in the function

class Subtract:
#left_formula - right_formula
    def __init__(self, left_formula, right_formula):
        self.nom = "Subtract"
        self.left_formula = left_formula
        self.right_formula = right_formula

        if self.left_formula.range is None or self.right_formula.range is None:
            self.range = None
        else:
            A = left_formula.range[0] - right_formula.range[1]
            B = left_formula.range[1] - right_formula.range[0]
            self.range = [A, B]
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
        res = []
        left_formula_robustness = self.left_formula.eval(traces)
        right_formula_robustness = self.right_formula.eval(traces)
        return np.subtract(left_formula_robustness,right_formula_robustness)

class GreaterThan:
# left_formula > right_formula ?
    def __init__(self, left_formula, right_formula):
        if isinstance(left_formula, (int, float)):
            left_formula = Const(left_formula)
        if isinstance(right_formula, (int, float)):
            right_formula = Const(right_formula)
        self.left_formula = left_formula
        self.right_formula = right_formula

        if left_formula.range is None or right_formula.range is None:
            self.range = None
        else:
            A = left_formula.range[0] - right_formula.range[0]
            B = left_formula.range[1] - right_formula.range[1]
            if (A > B):
                temp = A
                A = B
                B = temp
            self.range = [A, B]
        self.horizon = 0
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
    #return the difference between the left and the right formula : if it is positive the lessThan is true, otherwise it is false
        return Subtract(self.left_formula,self.right_formula).eval(traces)

class LessThan:
# left_formula < right_formula ?
    def __init__(self, left_formula, right_formula):
        self.nom = "LessThan"
        self.left_formula = left_formula
        self.right_formula = right_formula
        A = right_formula.var_range[0] - left_formula.var_range[0]
        B = right_formula.var_range[1] - left_formula.var_range[1]
        if (A > B):
            temp = A
            A = B
            B = temp
        self.var_range = [A, B]
        self.horizon = 0
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
    #return the difference between the right and the left formula : if it is positive the lessThan is true, otherwise it is false
        return Subtract(self.right_formula,self.left_formula).eval(traces)


class Abs:
# absolute value of the formula at a given time
    def __init__(self, formula):
        self.nom = "Abs"
        self.formula = formula
        A = np.abs(formula.var_range[0])
        B = np.abs(formula.var_range[1])
        if (A > B):
            temp = A
            A = B
            B = temp
        self.var_range = [A, B]
        self.variables = self.formula.variables
        self.horizon = 0
        self.arity = 1

    def eval(self, traces):
        formula_robustness = self.formula.eval(traces)
        return np.absolute(formula_robustness)

class Sum:
# left_formula + right_formula at a given time
    def __init__(self, left_formula, right_formula):
        self.nom = "Sum"
        self.left_formula = left_formula
        self.right_formula = right_formula
        A = left_formula.var_range[0] + right_formula.var_range[0]
        B = left_formula.var_range[1] + right_formula.var_range[1]
        self.var_range = [A, B]
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
        res = []
        left_formula_robustness = self.left_formula.eval(traces)
        right_formula_robustness = self.right_formula.eval(traces)
        return np.add(left_formula_robustness,right_formula_robustness)

class Implication:
    def __init__(self, left_formula, right_formula):
        self.nom = "Implication"
        self.left_formula = left_formula
        self.right_formula = right_formula
        A = max(-1*self.left_formula.var_range[1], self.right_formula.var_range[0])
        B = max(-1*self.left_formula.var_range[0], self.right_formula.var_range[1])
        self.var_range = [A, B]
        self.horizon = max(self.left_formula.horizon, self.right_formula.horizon)
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
        return Or(Not(self.left_formula),self.right_formula).eval(traces)

class Equals:
    def __init__(self, left_formula, right_formula):
        self.nom = "Equals"
        self.left_formula = left_formula
        self.right_formula = right_formula
        A = -1*np.abs(right_formula.var_range[0] - left_formula.var_range[0])
        B = -1*np.abs(right_formula.var_range[1] - left_formula.var_range[1])
        if A > B :
            temp = A
            A = B
            B = temp 
        self.var_range = [A, B]
        self.horizon = 0
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
        self.arity = 2

    def eval(self, traces):
    # Compute -|left_formula - right_formula|for each time. If this is nonzero, return as is.
    # Otherwise return 1.
        formula_robustness = Not(Abs(Subtract(self.left_formula,self.right_formula))).eval(traces)
        return np.where(formula_robustness == 0, 1, formula_robustness)	

class Not:
    def __init__(self, formula):
        self.nom = "Not"
        self.formula = formula
        A = -1*formula.var_range[0] 
        B = -1*formula.var_range[1] 
        if A > B :
            temp = A
            A = B
            B = temp
        self.var_range = [A, B]
        self.horizon = self.formula.horizon
        self.variables = self.formula.variables
        self.arity = 1


    def eval(self, traces):
        formula_robustness = self.formula.eval(traces)
        return formula_robustness*-1


class Next:
#Return the value at the next state
    def __init__(self, formula):
        self.nom = "Next"
        self.formula = formula
        self.var_range = formula.var_range
        self.horizon = 1 + self.formula.horizon
        self.variables = self.formula.variables
        self.arity = 1

    def find_next(self,traces):
        indice = -1
        for i in range(len(traces.timestamps)):
            if (traces.timestamps[i] == time):
                indice = i
        if indice == -1:
            raise Exception("time error") 
        else:
            if len(traces.timestamps) == indice+1:
                return traces.timestamps[indice]
            else:
                #Add +1 to return the index of the next state
                return traces.timestamps[indice+1]
        

    def eval(self, traces):
        formula_robustness = self.formula.eval(traces)
        res = np.roll(formula_robustness, -1)
        res[len(res) - 1] = res[len(res) - 2]
        return res


class Global:
#formula has to be True on the entire subsequent path
    def __init__(self, lower_time_bound, upper_time_bound, formula):
        self.nom = "Global"
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.formula = formula
        self.range = None if formula.range is None else formula.range.copy()
        self.horizon = self.upper_time_bound + self.formula.horizon
        self.variables = self.formula.variables

    def eval(self, traces):
        robustness = self.formula.eval(traces)
        result = np.empty(shape=(len(robustness)))
        for current_time_pos in range(len(traces.timestamps) - 1, -1, -1):
            # Lower and upper times for the current time.
            lower_bound = traces.timestamps[current_time_pos] + self.lower_time_bound
            upper_bound = traces.timestamps[current_time_pos] + self.upper_time_bound

            # Find the corresponding positions in timestamps.
            lower_bound_pos = traces.search_time_index(lower_bound, start=current_time_pos)
            upper_bound_pos = traces.search_time_index(upper_bound, start=lower_bound_pos)

            # Find minimum between the positions.
            if lower_bound_pos == -1:
                r = float("inf")
            else:
                start_pos = lower_bound_pos
                end_pos = upper_bound_pos + 1 if upper_bound_pos >= 0 else len(traces.timestamps)
                r = np.min(robustness[start_pos: end_pos])

            result[current_time_pos] = r

        return result

#formula eventually has to be True (somewhere on the subsequent path)
class Finally:
    def __init__(self, lower_time_bound, upper_time_bound, formula):
        self.nom = "Finally"
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.formula = formula
        self.var_range = formula.var_range
        self.horizon = self.upper_time_bound + self.formula.horizon
        self.variables = self.formula.variables

    def eval(self, traces):
        formula_robustness = Not(Global(self.lower_time_bound,self.upper_time_bound,Not(self.formula)))
        return formula_robustness.eval(traces)

class Or(STL):

    def __init__(self, *args, nu=1):
        self.formula = Not(And(*[Not(f) for f in args], nu=nu))

    def eval(self, traces):
        return self.formula.eval(traces)

class And:

    def __init__(self, *args, nu=1):
        self.formulas = list(args)
        self.nu = nu
        
        if self.nu <= 0:
            raise ValueError("The nu parameter must be positive.")

        self.variables = sum([f.variables for f in self.formulas], start=[])

        self.horizon = max(f.horizon for f in self.formulas)

        A = [f.range[0] if f.range is not None else None for f in self.formulas]
        B = [f.range[1] if f.range is not None else None for f in self.formulas]
        if None in A or None in B:
            self.range = None
        else:
            self.range(min(A), min(B))
        self.effective_range = None

    def eval2(self, traces):
        """This is the usual and."""

        # Evaluate the robustness of all subformulas and save the robustness
        # signals into one 2D array.
        M = len(self.formulas)
        for i in range(M):
            r = self.formulas[i].eval(traces)
            if i == 0:
                rho = np.empty(shape=(M, len(r)))
            rho[i,:] = r

        return np.min(rho, axis=0)

    def eval(self, traces):
        """This is the alternative one."""

        # Evaluate the robustness of all subformulas and save the robustness
        # signals into one 2D array.
        M = len(self.formulas)
        for i in range(M):
            r = self.formulas[i].eval(traces)
            if i == 0:
                rho = np.empty(shape=(M, len(r)))
            rho[i,:] = r

        rho_min = np.min(rho, axis=0)

        robustness = np.empty(shape=(len(rho_min)))
        for i in range(len(rho_min)):
            # TODO: Would it make sense to compute rho_tilde for the complete
            # x-axis in advance? Does it use potentially much memory for no
            # speedup?
            rho_tilde = rho[:,i]/rho_min[i] - 1

            if rho_min[i] < 0:
                numerator = rho_min[i] * np.sum(np.exp((1+self.nu) * rho_tilde))
                denominator = np.sum(np.exp(self.nu * rho_tilde))
            elif rho_min[i] > 0:
                numerator = np.sum(np.multiply(rho[:,i], np.exp(-self.nu * rho_tilde)))
                denominator = np.sum(np.exp(-1 * self.nu * rho_tilde))
            else:
                numerator = 0
                denominator = 1

            robustness[i] = numerator/denominator
        
        return robustness

# left_formula has to hold at least until right_formula; if right_formula never becomes true, left_formula must remain true forever. 
class Weak_Until:
    def __init__(self,lower_time_bound,upper_time_bound,left_formula,right_formula):
        self.nom = "Until"
        self.left_formula = left_formula
        self.right_formula = right_formula
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.var_range = left_formula.var_range
        self.horizon = self.upper_time_bound +  max(self.left_formula.horizon, self.right_formula.horizon)
        self.variables = list(set(self.left_formula.variables + self.right_formula.variables))

    def eval(self, traces,time):
        i = 0
        #finding the first index
        while  traces.timestamps[i] < self.lower_time_bound:  
            i += 1

        #initialistion with the higest value
        min_left_formula = self.var_range[1]

        #evaluate the left formulas
        left_formula_robustness = self.left_formula.eval(traces)
        right_formula_robustness = self.right_formula.eval(traces)
        
        #if the time bound is exceed or if the right_formula is True
        while  i < len(traces.timestamps) and traces.timestamps[i] <= self.upper_time_bound and right_formula_robustness[i] < 0:
            

            #finding the minimum of the left formula
            if min_left_formula > left_formula_robustness[i]:
                min_left_formula = left_formula_robustness[i]
            i += 1
        #return the minimum of the left formula
        return np.full(len(left_formula_robustness),min_left_formula)



"""
#left_formula has to hold at least until right_formula becomes true, which must hold at the current or a future position. 
class Until:

	def __init__(self,lower_time_bound,upper_time_bound,left_formula,right_formula):
		self.nom = "Until"
		self.left_formula = left_formula
		self.right_formula = right_formula
		self.upper_time_bound = upper_time_bound
		self.lower_time_bound = lower_time_bound
		A = min(self.left_formula.var_range[0], self.right_formula.var_range[0])
		B = max(self.left_formula.var_range[1], self.right_formula.var_range[1])
		self.var_range = [A, B]
		self.horizon = self.upper_time_bound +  max(self.left_formula.horizon, self.right_formula.horizon)
		self.variables = list(set(self.left_formula.variables + self.right_formula.variables))

	
	def eval(self, traces,time):
		i = 0
		#finding the first index
		while  traces.timestamps[i] < self.lower_time_bound:
			i += 1

		min_left_formula = self.var_range[1]
		min_right_formula = self.var_range[1]
		max_right_formula = self.var_range[0]
		#if the time bound is exceed or if the right_formula is True when left_formula is need to be True
		while  i < len(traces.timestamps) and traces.timestamps[i] <= self.upper_time_bound & self.right_formula.eval(traces, traces.timestamps[i]) < 0:
			left_formula_evaluation = self.left_formula.eval(traces, traces.timestamps[i])
			right_formula_evaluation = self.right_formula.eval(traces, traces.timestamps[i])
			#Finding the min of the left_formula
			if min_left_formula > left_formula_evaluation:
				min_left_formula = left_formula_evaluation
			#Finding the max of the right_formula
			if max_right_formula < right_formula_evaluation:
				max_right_formula = right_formula_evaluation
			i += 1

		#if the time bound is exceed
		if traces.timestamps[i] > self.upper_time_bound:
			#return Negative Value
			return max_right_formula
		elif self.right_formula.eval(traces, traces.timestamps[i]) > 0:
			# right_formula need to stay True
			while  traces.timestamps[i] <= self.upper_time_bound:
				#Finding the min of the right_formula
				right_formula_evaluation = self.right_formula.eval(traces, traces.timestamps[i])
				if min_right_formula > right_formula_evaluation:
					min_right_formula = right_formula_evaluation
				i += 1
				return min_right_formula

		return min_left_formula

# left_formula has to be true until and including the point where right_formula first becomes true; if right_formula never becomes true, left_formula must remain true forever.
class Release:
	def __init__(self,lower_time_bound,upper_time_bound,left_formula,right_formula):
		self.nom = "Release"
		self.left_formula = left_formula
		self.right_formula = right_formula
		self.upper_time_bound = upper_time_bound
		self.lower_time_bound = lower_time_bound
		self.var_range = left_formula.var_range
		self.horizon = self.upper_time_bound +  max(self.left_formula.horizon, self.right_formula.horizon)
		self.variables = list(set(self.left_formula.variables + self.right_formula.variables))
	
	def eval(self, traces,time):
		i = 0
		#finding the first index
		while  traces.timestamps[i] < self.lower_time_bound:  
			i += 1

		#initialistion with the higest value
		min_left_formula = self.var_range[1]

		#if the time bound is exceed or if the right_formula is True when left_formula is need to be True
		while  i < len(traces.timestamps) and traces.timestamps[i] <= self.upper_time_bound & self.right_formula.eval(traces, traces.timestamps[i-1]) < 0:
			#evaluate the left formula
			left_formula_evaluation = self.left_formula.eval(traces, traces.timestamps[i])
			#finding the minimum of the left formula
			if min_left_formula > left_formula_evaluation:
				min_left_formula = left_formula_evaluation
			i += 1
		#return the minimum of the left formula
		return min_left_formula
		"""
