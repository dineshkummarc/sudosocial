#!/usr/bin/env python

# CRON Bootstrap
import config
import sys
sys.path.append(config.path)
from django.core.management import setup_environ
import settings
setup_environ(settings)

# Imports for this cron
import datetime
import logging

from django.db import IntegrityError
import django.utils.hashcompat as hashcompat
import feedparser
import jsonpickle

import lifestream.models

logging.basicConfig( level = logging.DEBUG, format = '%(asctime)s %(levelname)s %(message)s', )
log = logging.getLogger()

def cron_fetch_feeds():
    """ """
    newEntryCount = 0
    feeds = lifestream.models.Feed.objects.all()
    for feed in feeds:
        stream = feedparser.parse(feed.url)
        if 1 == stream.bozo and 'bozo_exception' in stream.keys():
            log.error('Unable to fetch %s Exception: %s', feed.url, stream.bozo_exception)
        else:
            log.info('Processing %s', feed.url)
            if 'feed' in stream and 'title' in stream.feed:
                log.info('Processing title: %s', stream.feed.title)
            if 'feed' in stream and 'title' in stream.feed and feed.title != stream.feed.title:
                feed.title = stream.feed.title
                try:
                    feed.save()
                except Exception, x:
                    log.error("Unable to update feed title from=%s to=%s" % (feed.title, stream.title))
                    log.error(x)
            else:
                if (not 'feed' in stream) or (not 'title' in stream.feed):
                    log.warn("Feed doesn't have a title property")
                    log.info(stream)
            for entry in stream.entries:
                
                jsonEntry = jsonpickle.encode(entry)
                entryGuid = ''
                if 'guid' in entry:
                    entryGuid = entry.guid
                else:
                    entryGuid = hashcompat.md5_constructor(jsonEntry).hexdigest()
                yr, mon, d, hr, min, sec = entry.updated_parsed[:-3]
                lastPub = datetime.datetime(yr, mon, d, hr, min, sec)
                newEntry = lifestream.models.Entry(feed=feed, guid=entryGuid, raw=jsonEntry, last_published_date=lastPub)
                try:
                    newEntry.save()
                    newEntryCount += 1
                except IntegrityError, e:
                    log.info('Skipping duplicate entry %s, caught error: %s', entryGuid, e)
    return 'Finished importing %d items' % newEntryCount

cron_fetch_feeds()