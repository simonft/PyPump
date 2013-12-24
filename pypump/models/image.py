##
# Copyright (C) 2013 Jessica T. (Tsyesika) <xray7224@googlemail.com>
# 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU General Public License for more details. 
# 
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##

import logging
import mimetypes
import os

from dateutil.parser import parse

from pypump.models import (AbstractModel, Postable, Likeable, Commentable,
                           Deleteable, Shareable)

_log = logging.getLogger(__name__)

class ImageContainer(object):
    """ Container to hold about a specific image """
    def __init__(self, url, width, height):
        self.url = url
        self.width = width
        self.height = height

    def __repr__(self):
        return "<Image {width}x{height}".format(
            width=self.width,
            height=self.height
        )

class Image(AbstractModel, Postable, Likeable, Shareable, Commentable, Deleteable):
    
    url = None
    actor = None
    author = actor
    summary = None
    display_name = None
    id = None
    updated = None
    published = None

    @property
    def ENDPOINT(self):
        return "/api/user/{username}/feed".format(self._pump.client.nickname)

    def __init__(self, id=None, url=None, display_name=None, content=None, 
                 actor=None, published=None, updated=None, *args, **kwargs):

        super(Image, self).__init__(*args, **kwargs)

        self.id = id
        self.display_name = display_name
        self.content = content
        self.actor = actor or self.actor
        self.url = url
        self.published = published
        self.updated = updated

    def __repr__(self):
        if self.actor is None:
            return "<{type}>".format(type=self.TYPE)

        return "<{type} by {webfinger}>".format(
            type=self.TYPE,
            webfinger=self.actor.webfinger)


    def from_file(self, filename):
        """ Uploads an image from a filename """
        mimetype = mimetypes.guess_type(filename)[0] or "application/octal-stream"
        headers = {
            "Content-Type": mimetype,
            "Content-Length": os.path.getsize(filename),
        }

        params = {"qqfile": filename.split("/")[-1]}

        if self.display_name is not None:
            params["title"] = self.display_name
        if self.content is not None:
            params["description"] = self.content
        
        image = self._pump.request(
                "/api/user/{0}/uploads".format(self._pump.client.nickname),
                method="POST",
                data=open(filename, "rb").read(),
                headers=headers,
                params=params,
                )

        self.unserialize(image)

        # now send it to the feed
        data = {
            "verb": "post",
            "object": image,
        }

        data.update(self.serialize())

        # send it to the feed
        image_feed = self._pump.request(
                "/api/user/{0}/feed".format(self._pump.client.nickname),
                method="POST",
                data=data,
                )

        _log.debug(image_feed)
        self.unserialize(image_feed)
        return self

    def unserialize(self, data):
        image = type(self)(id=data.get("id", None))

        if "fullImage" in data:
            full_image = data["fullImage"]
            image.original = ImageContainer(
                url=full_image["url"],
                height=full_image.get("height"),
                width=full_image.get("width")
            )
            
        if "image" in data:
            save_point = "original" if not hasattr(image, "original") else "thumbnail"
            thumbnail = data["image"]
            setattr(image, save_point, ImageContainer(
                url=thumbnail["url"],
                height=thumbnail.get("height"),
                width=thumbnail.get("width")
            ))

        image.author = self._pump.Person().unserialize(data["author"]) if "author" in data else None

        image.add_links(data)
        image.published = parse(data["published"]) if "published" in data else None
        image.updated = parse(data["updated"]) if "updated" in data else None
        image.deleted = parse(data["deleted"]) if "deleted" in data else None
        image.display_name = data.get("displayName", "")
        image.summary = data.get("summary", "")
        image.url = data.get("url")
        image.content = data.get("content", "")
 
        return image
