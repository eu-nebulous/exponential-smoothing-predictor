from influxdb_client import InfluxDBClient, Point, WritePrecision
from datetime import datetime
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
from runtime.operational_status.EsPredictorState import EsPredictorState

#import influxdb_client, os, time
#from influxdb_client import InfluxDBClient, Point, WritePrecision
#from influxdb_client.client.write_api import SYNCHRONOUS

#token = Constants.token
#org = "nebulous"
#url = "http://localhost:8086"

#write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

#bucket="nebulous"

#write_api = client.write_api(write_options=SYNCHRONOUS)
#
#for value in range(5):
#    point = (
#        Point("measurement1")
#        .tag("tagname1", "tagvalue1")
#        .field("field1", value)
#    )
#    write_api.write(bucket=bucket, org="nebulous", record=point)
#    time.sleep(1) # separate points by 1 second


#data = [
#    {
#       "measurement": "temperature",
#        "tags": {"location": "Prague"},
#        "fields": {"temperature": 25.3}
#    }
#]




class InfluxDBConnector:

    def __init__(self):
        self.client = InfluxDBClient(url="http://" + EsPredictorState.influxdb_hostname + ":" + str(EsPredictorState.influxdb_port), token=EsPredictorState.influxdb_token, org=EsPredictorState.influxdb_organization)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        logging.info("Successfully created InfluxDB connector, client is "+str(self.client))
    def write_data(self,data,bucket):
        self.write_api.write(bucket=bucket, org=EsPredictorState.influxdb_organization, record=data, write_precision=WritePrecision.S)

    def get_data(self):
        query_api = self.client.query_api()
        query = """from(bucket: "nebulous")
         |> range(start: -1m)
         |> filter(fn: (r) => r._measurement == "temperature")"""
        tables = query_api.query(query, org=EsPredictorState.influxdb_organization)

        for table in tables:
            for record in table.records:
                print(record)