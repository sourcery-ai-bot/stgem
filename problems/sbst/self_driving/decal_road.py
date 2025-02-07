import json
import uuid
from typing import Tuple, List


class DecalRoad:
    DEFAULT_MATERIAL = 'tig_road_rubber_sticky'

    def __init__(self, name,
                 material=DEFAULT_MATERIAL,
                 persistentId=None,
                 drivability=1):
        self.name = name
        self.material = material
        self.persistentId = persistentId if persistentId else str(uuid.uuid4())
        self.nodes = []
        self.drivability = drivability

    def add_4d_points(self, nodes: List[Tuple[float, float, float, float]]):
        self._safe_add_nodes(nodes)
        assert nodes, 'nodes should be a non empty list'
        assert all(len(item) == 4 for item in nodes), 'nodes list should contain tuple of 4 elements'
        assert all(all(isinstance(val, float) for val in item) for item in nodes), \
                'points list can contain only float'
        self.nodes += [list(item) for item in nodes]
        return self

    def to_dict(self):
        return {
            'name': self.name,
            'nodes': self.nodes
        }

    @classmethod
    def from_dict(cls, d):
        return DecalRoad(name=d['name']).add_4d_points(nodes=d['nodes'])

    def _safe_add_nodes(self, nodes: List):
        l = len(nodes) + len(self.nodes)
        #assert l < 540, f'BeamNG has issues with roads with more than 540 points. This road would have {l} nodes'

    def to_json(self):
        assert len(self.nodes) > 0, 'there are no points in this road'
        roadobj = {
            'name': self.name,
            'class': 'DecalRoad',
            'breakAngle': 180,
            'distanceFade': [1000, 1000],
            'drivability': self.drivability,
            'material': self.material,
            'overObjects': True,
            'persistentId': self.persistentId,
            '__parent': 'generated',
            'position': tuple(self.nodes[0][:3]),
            'textureLength': 2.5,
            'nodes': self.nodes,
        }
        return json.dumps(roadobj)
