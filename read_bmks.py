#!/usr/bin/env python3
"""A quick script to read bookmarks from Mozilla JSON export format."""

# pylint: disable=C0103,R0902,R0913,R0903

import json

MARK_TYPES = ('text/x-moz-place-container',
              'text/x-moz-place-separator',
              'text/x-moz-place')

class PlaceContainer():
    """A container/folder for bookmarks."""

    MIME_TYPE = 'text/x-moz-place-container'

    def __init__(self, annos, children, dateAdded, guid, _id, index, lastModified, root, title,
                 typeCode):
        """Parameters are drawn from JSON structure, omitting 'type' which is always MIME_TYPE."""
        self.annos = annos
        self.children = children
        self.dateAdded = dateAdded
        self.guid = guid
        self._id = _id
        self.index = index
        self.lastModified = lastModified
        self.root = root
        self.title = title if title != '' else '/'
        self.typeCode = typeCode

    def __str__(self):
        """Show container title and index, hopefully (?) unique."""
        return '{} [{}]'.format(self.title, self.index)

    def collect_urls(self):
        """Return a list of the URIs of all the container's descendants."""
        urls = []
        for kid in self.children:
            urls.extend(kid.collect_urls())
        return urls

    @classmethod
    def fromJson(cls, markJson):
        """
        Construct a new PlaceContainer instance from the associated JSON structure.

        JSON structure should be as exported by Firefox for this MIME_TYPE.
        """
        def _(dictionary, key):
            return dictionary[key] if key in dictionary else ''

        if markJson['type'] != cls.MIME_TYPE:
            raise Exception('Attempted to create a PlaceContainer from item with type {}'.format(
                markJson['type']))

        return PlaceContainer(_(markJson, 'annos'), [], markJson['dateAdded'], markJson['guid'],
                              markJson['id'], markJson['index'], markJson['lastModified'],
                              _(markJson, 'root'), markJson['title'], markJson['typeCode'])


class PlaceSeparator():
    """A visual separator for bookmark lists."""

    MIME_TYPE = 'text/x-moz-place-separator'

    def __init__(self, dateAdded, guid, _id, index, lastModified, title, typeCode):
        """Create a new PlaceSeparator, params match the JSON fields (except 'type')."""
        self.dateAdded = dateAdded
        self.guid = guid
        self._id = _id
        self.index = index
        self.lastModified = lastModified
        self.title = title
        self.typeCode = typeCode

    @classmethod
    def fromJson(cls, markJson):
        """Construct a new `PlaceSeparator` from the JSON structure."""
        def _(d, key):
            return d[key] if key in d else ''

        if markJson['type'] != cls.MIME_TYPE:
            raise Exception('Attempted to create a {} from item with type {}'.format(
                cls.__name__, markJson['type']))

        return PlaceContainer(_(markJson, 'annos'), [], markJson['dateAdded'], markJson['guid'],
                              markJson['id'], markJson['index'], markJson['lastModified'],
                              _(markJson, 'root'), markJson['title'], markJson['typeCode'])

    def collect_urls(self):  # pylint: disable=R0201
        """Return URLs of this node and its descendants. Separator has neither, so always `[]`."""
        return []


class Place():
    """A standard bookmark with a URL target."""

    MIME_TYPE = 'text/x-moz-place'

    def __init__(self, annos, charset, dateAdded, guid, iconuri, _id, index, keyword,
                 lastModified, postData, tags, title, typeCode, uri):
        """Create a new bookmark from Firefox export fields."""
        self.annos = annos
        self.charset = charset
        self.dateAdded = dateAdded
        self.guid = guid
        self.iconuri = iconuri
        self._id = _id
        self.index = index
        self.keyword = keyword
        self.lastModified = lastModified
        self.postData = postData
        self.tags = tags
        self.title = title
        self.typeCode = typeCode
        self.uri = uri

    def __str__(self):
        return '{}: {}'.format(self.title, self.uri)

    def collect_urls(self):
        """Return a list this node's URI."""
        return [self.uri]

    @classmethod
    def fromJson(cls, markJson: dict) -> 'Place':
        """Create a Place object from the supplied dictionary."""
        def _(d, key):
            return d[key] if key in d else ''
        if markJson['type'] != cls.MIME_TYPE:
            raise Exception('Attempted to create a {} from item with type {}'.format(
                cls.__name__, markJson['type']))

        return Place(_(markJson, 'annos'), _(markJson, 'charset'), markJson['dateAdded'],
                     markJson['guid'], _(markJson, 'iconuri'), markJson['id'], markJson['index'],
                     _(markJson, 'keyword'), markJson['lastModified'], _(markJson, 'postData'),
                     _(markJson, 'tags'), markJson['title'], markJson['typeCode'],
                     _(markJson, 'uri'))

def parseMark(markJson):
    """Parse a bookmark from dictionary `markJson`, recursively parsing its children."""
    theNode = None
    for cls in (Place, PlaceContainer, PlaceSeparator):
        if cls.MIME_TYPE == markJson['type']:
            theNode = cls.fromJson(markJson)

    if theNode is None:
        raise Exception("Didn't match the MIME type {}".format(markJson['type']))

    if 'children' in markJson:
        for kidJSON in markJson['children']:
            assert isinstance(kidJSON, dict)
            theNode.children.append(parseMark(kidJSON))
    return theNode

def main():
    """Run the whole process, in a function to keep namespace clean."""
    with open('data/bookmarks-2018-10-09.json', 'r') as marks_in:
        marks = json.load(marks_in)

    structure = parseMark(marks)
    print(structure)
    for place in structure.children:
        print('    ' + str(place))
        for kid in place.children:
            print('    ' * 2 + str(kid))

    all_urls = structure.collect_urls()
    print('Found {:,} bookmarks.'.format(len(all_urls)))

    print("found {:,} unique bookmarks.".format(len(set(all_urls))))


if __name__ == '__main__':
    main()
