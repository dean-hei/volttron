# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright (c) 2015, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those
# of the authors and should not be interpreted as representing official
# policies,
# either expressed or implied, of the FreeBSD Project.
#

# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization
# that has cooperated in the development of these materials, makes
# any warranty, express or implied, or assumes any legal liability
# or responsibility for the accuracy, completeness, or usefulness or
# any information, apparatus, product, software, or process disclosed,
# or represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does
# not necessarily constitute or imply its endorsement, recommendation,
# r favoring by the United States Government or any agency thereof,
# or Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830

# }}}

from __future__ import absolute_import

import logging
import sys

from volttron.platform.agent import utils
from volttron.platform.agent.base_aggregate_historian import AggregateHistorian
from volttron.platform.dbutils import mongoutils

utils.setup_logging(logging.DEBUG)
_log = logging.getLogger(__name__)
__version__ = '1.0'


class MongoAggregateHistorian(AggregateHistorian):
    """
    Agent to aggregate data in historian based on a specific time period.
    This aggregegate historian aggregates data collected by mongo historian.
    """

    def __init__(self, config_path, **kwargs):
        """
        Validate configuration, create connection to historian, create
        aggregate tables if necessary and set up a periodic call to
        aggregate data
        :param config_path: configuration file path
        :param kwargs:
        """
        super(MongoAggregateHistorian, self).__init__(config_path, **kwargs)

        connection = self.config.get('connection')
        self.dbclient = mongoutils.get_mongo_client(connection['params'])

        # Why are we not letting users configure data and topic collection
        # names in mongo similar to sqlhistorian
        # tables_def = sqlutils.get_table_def(self.config)
        self._data_collection = 'data'
        self._meta_collection = 'meta'
        self._topic_collection = 'topics'

        # 2. load topic name and topic id.
        self.topic_id_map, name_map = self.get_topic_map()

    def get_topic_map(self):
        return mongoutils.get_topic_map(self.dbclient, 'topics')

    def is_supported_aggregation(self, agg_type):
        return agg_type.upper() in ['SUM', 'COUNT', 'AVG', 'MIN', 'MAX',
                                    'STDDEVPOP', 'STDDEVSAMP']

    def create_aggregate_store(self, param, agg_time_period):
        pass

    def collect_aggregate(self, topic_id, agg_type, start_time, end_time):

        db = self.dbclient.get_default_database()
        _log.debug("collect_aggregate: params {}, {}, {}, {}".format(
            topic_id, agg_type, start_time, end_time))

        match_conditions = [{"topic_id": topic_id}]
        if start_time is not None:
            match_conditions.append({"ts": {"$gte": start_time}})
        if end_time is not None:
            match_conditions.append({"ts": {"$lt": end_time}})

        match = {"$match": {"$and": match_conditions}}
        group = {"$group": {"_id": "null", "count": {"$sum": 1},
                            "aggregate": {"$" + agg_type: "$value"}}}

        pipeline = [match, group]

        _log.debug("collect_aggregate: pipeline: {}".format(pipeline))
        cursor = db[self._data_collection].aggregate(pipeline)

        row = cursor.next()
        _log.debug("collect_aggregate: got result as {}".format(row))
        return row['aggregate'], row['count']

    def insert_aggregate(self, agg_type, period, end_time, topic_id, value):
        db = self.dbclient.get_default_database()
        table_name = agg_type + '''_''' + period
        db[table_name].replace_one(
            {'ts': end_time, 'topic_id': topic_id},
            {'ts': end_time, 'topic_id': topic_id, 'value': value},
            upsert=True)


def main(argv=sys.argv):
    """Main method called by the eggsecutable."""
    try:
        utils.vip_main(MongoAggregateHistorian)
    except Exception as e:
        _log.exception('unhandled exception' + e.message)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
