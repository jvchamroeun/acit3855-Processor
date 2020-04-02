from json import JSONDecodeError

import connexion
from connexion import NoContent
import yaml
import logging.config
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import json
import requests
from flask_cors import CORS, cross_origin

try:
    with open('/config/app_conf.yml', 'r') as f:
        app_config = yaml.safe_load(f.read())
except IOError:
    with open('app_conf.yml', 'r') as f:
        app_config = yaml.safe_load(f.read())


with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')


def populate_stats():
    """ Periodically update stats """
    logger.info("Start Periodic Processing")

    try:
        with open(app_config['datastore']['filename'], 'r') as d:
            json_data = json.load(d)
    except FileNotFoundError:
        json_data = {}

    url_1 = app_config['eventstore']['url1']
    url_2 = app_config['eventstore']['url2']
    time_now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    if not json_data.get('num_booking_deliveries'):
        json_data['num_booking_deliveries'] = 0
    if not json_data.get('num_freights_assigned'):
        json_data['num_freights_assigned'] = 0
    if not json_data.get('updated_timestamp'):
        json_data['updated_timestamp'] = "2020-01-01T01:00:00"

    parameter = {
        "startDate": json_data["updated_timestamp"],
        "endDate": time_now
    }

    r1 = requests.get(url=url_1, params=parameter)
    data_r1 = len(r1.json())

    if r1.status_code == 400:
        logger.error("Bad Request - 400")
    elif r1.status_code == 200:
        logger.info(data_r1)

    r2 = requests.get(url=url_2, params=parameter)
    data_r2 = len(r2.json())

    if r2.status_code == 400:
        logger.error("Bad Request - 400")
    elif r2.status_code == 200:
        logger.info(data_r2)

    json_data['num_booking_deliveries'] = len(r1.json())
    json_data['num_freights_assigned'] = len(r2.json())
    json_data['updated_timestamp'] = time_now

    with open(app_config['datastore']['filename'], 'w') as wr:
        wr.write(json.dumps(json_data, indent=2))

    logger.debug("Updated Statistics, " +
                 "{ " + str(data_r1) + ", " +
                 str(data_r2) + ", " + str(time_now) + " }")
    logger.info("Period Processing Ended")


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,
                  'interval',
                  seconds=app_config['scheduler']['period_sec'])
    sched.start()


def get_delivery_stats():
    """Get delivery stats from the data store"""
    logger.info("Requested has started")

    try:
        with open(app_config['datastore']['filename'], 'r') as file:
            json_data = json.load(file)
    except IOError:
        return "File not accessible", 404

    dict = {}
    dict['num_booking_deliveries'] = json_data['num_booking_deliveries']
    dict['num_freights_assigned'] = json_data['num_freights_assigned']
    dict['updated_timestamp'] = json_data['updated_timestamp']

    logger.debug("Python Dict. Content: " + str(dict))
    logger.info("Requested has ended")

    return dict, 200


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml")
CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'


if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, use_reloader=False)
