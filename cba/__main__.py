#/usr/bin/env python3

import os
import logging

from SCIM import SCIM
from AMQP import AMQP

log_level = os.environ.get('LOG_LEVEL', 'ERROR')

logging.basicConfig(
    level=logging.getLevelName(log_level),
    format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger()

if __name__ == "__main__":

  with SCIM(
        os.environ.get('SCIM_SERVER', 'http://localhost'),
        os.environ.get('SCIM_BEARER', None),
        verify=(os.environ.get('SCIM_VERIFY', "True").upper() == 'TRUE'),
        broker = None
    ) as my_scim:

      def user(id):
        logger.info(f"[USER:{id}] Notification received !")
        my_scim.get_user(id)
        logger.info(my_scim)

      def group(id):
        logger.info(f"[GROUP:{id}] Notification received !")
        my_scim.get_group(id)
        logger.info(my_scim)

      AMQP(os.environ['URI']).subscribe({
          'user': user,
          'group': group
        }
      )
