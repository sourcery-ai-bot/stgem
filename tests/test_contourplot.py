import os, math, unittest

from stgem.budget import Budget
from stgem.generator import STGEM, Search, STGEMResult
from stgem.sut.python import PythonFunction
from stgem.objective import Minimize
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform

from stgem.analyze import XXX

def myfunction(input: [[-15, 15], [-15, 15] ) -> [[0, 350], [0, 350], [0, 350]]:
    x1, x2 = input[0], input[1]
    h1 = 305 - 100 * (math.sin(x1 / 3) + math.sin(x2 / 3) + math.sin(x3 / 3))
    h2 = (x1 - 7) ** 2 + (x2 - 7) ** 2 + (x3 - 7) ** 2 - (
            math.cos((x1 - 7) / 2.75) + math.cos((x2 - 7) / 2.75) + math.cos((x3 - 7) / 2.75))

    return [h1, h2]

class MyTestCase(unittest.TestCase):
    def test_dump(self):
        generator = STGEM(
            description="test-dump",
            sut=PythonFunction(function=myfunction),
            objectives=[Minimize(selected=[0, 1], scale=True)],
            steps=[
                Search(budget_threshold={"executions": 20},
                       algorithm=Random(model_factory=(lambda: Uniform())))
            ]
        )

        r = generator.run()
        
        XXX (r.test_repository , output_n=0 )

if __name__ == "__main__":
    unittest.main()

