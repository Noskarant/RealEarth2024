from unittest.mock import MagicMock
import requests
from osm_microdetails import query_osm


def test_post_406_retries_get():
    client=MagicMock()
    post=client.post.return_value
    post.raise_for_status.side_effect=requests.HTTPError('406 Not Acceptable')
    get=client.get.return_value
    get.json.return_value={'elements':[{'type':'node','id':1,'lat':45.5,'lon':4.6}]}
    data=query_osm((4.631,45.58),3000,session=client,endpoint='https://overpass-api.de/api/interpreter')
    assert data['elements'][0]['id']==1
    assert data['provenance']['method']=='get'
    assert client.get.call_args.kwargs['params']['data'].startswith('[out:json]')
