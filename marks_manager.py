#!/usr/bin/env python3
"""A quick script to read bookmarks from Mozilla JSON export format."""

# Copyright 2021 by Adrian L. Flanagan
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# pylint: disable=C0103,R0902,R0913,R0903

from collections import defaultdict
import sys
import json
import argparse
import requests

from requests.exceptions import ConnectionError as RequestsConnectionError, InvalidSchema
from requests.status_codes import codes

MARK_TYPES = ('text/x-moz-place-container',
              'text/x-moz-place-separator',
              'text/x-moz-place')


class PlaceContainer:
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


def consume_args(arguments):
    """
    Process command-line arguments.

    Handles bad input and -h/--help. Otherwise returns a `Namespace` object with the given
    argument values.
    """
    parser = argparse.ArgumentParser(
        description='Process a Firefox bookmarks file, report duplicates or dead links.')
    parser.add_argument('backup_file', type=argparse.FileType(mode='r'),
                        help='A Firefox bookmarks backup (not export) file, in JSON format.')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
    parser.add_argument('--dead', action='store_true',
                        help='Attempt to contact each link, report links with errors.')
    parser.add_argument('--noduplicates', action='store_true',
                        help='Disable (default enabled) checking for duplicate links.')
    parser.add_argument('--limit', type=int,
                        help='Limit number of links for dead link check (mostly for testing)',
                        default=-1)
    return parser.parse_args(arguments)


def parseMark(markJson):
    """Parse a bookmark from dictionary `markJson`, recursively parsing its children."""
    theNode = None
    for cls in (Place, PlaceContainer, PlaceSeparator):
        if cls.MIME_TYPE == markJson['type']:
            theNode = cls.fromJson(markJson)
            break

    if theNode is None:
        raise Exception("Didn't match the MIME type {}".format(markJson['type']))

    if 'children' in markJson:
        for kidJSON in markJson['children']:
            assert isinstance(kidJSON, dict)
            theNode.children.append(parseMark(kidJSON))
    return theNode

def walk_tree(bookmark, container_path):
    if isinstance(bookmark, PlaceSeparator):
        return
    if isinstance(bookmark, Place):
        yield (container_path, bookmark, )
    if isinstance(bookmark, PlaceContainer):
        new_path = "/".join((container_path, bookmark.title, )) if bookmark.title and bookmark.title != "/" else container_path
        for kid in bookmark.children:
            yield from walk_tree(kid, new_path)

def find_dupes(bookmarks):
    """Walk the structure of parsed bookmarks, finding duplicate URLs."""
    dupes = defaultdict(list)
    for path, bkmk in walk_tree(bookmarks, ""):
        dupes[bkmk.uri].append(path)
    return {key: dupes[key] for key in dupes if len(dupes[key]) > 1}

def find_duplicated_paths(bookmarks):
    paths = defaultdict(set)
    dupe_paths = []
    for path, bkmk in walk_tree(bookmarks, ""):
        paths[path].add(bkmk.uri)
    for key in paths:
        for other in paths:
            if key == other:
                continue
            if paths[key] == paths[other]:
                #  we find both (other, key) and (key, other) but for our purposes they're the same
                if (other, key, ) not in dupe_paths:
                    dupe_paths.append((key, other, ))
    return dupe_paths

def test_walk_tree(structure):
    with open('bookmark_titles.txt', 'w') as bkmk_out:
        for path, bookmark in walk_tree(structure, ""):
            bkmk_out.write('{}: {}\n'.format(path, bookmark))

_dot_count = 0
"""Global for communicating between procedures. Should make a class..."""
def status_update(successful):
    """Provide visual feedback for each dead link test."""
    global _dot_count
    print('.' if successful else 'x', end='', flush=True)
    _dot_count += 1
    if _dot_count > 80:
        print()
        _dot_count = 0

def verify_urls(urls, limit):
    """Attempt to contact each URL in `urls`, collect connection failures."""
    global _dot_count
    _dot_count = 0

    check_urls = list(urls)

    if limit != -1:
        check_urls = check_urls[:limit]

    bad_urls = {}

    print('\nTesting URLs:')
    for the_url in check_urls:
        if the_url.startswith('javascript:'):
            continue
        try:
            r = requests.get(the_url)
            if r.status_code != requests.codes.OK:  # pylint: disable=E1101
                bad_urls[the_url] = "Status Code {} ({})".format(r.status_code,
                                                                 codes[r.status_code])
                status_update(False)
            else:
                status_update(True)
        except TimeoutError:
            bad_urls[the_url] = "Timeout"
            status_update(False)
        except (ConnectionError, RequestsConnectionError):
            bad_urls[the_url] = "Connection failure"
            status_update(False)
        except InvalidSchema:
            bad_urls[the_url] = "Not a valid URL!!"
            status_update(False)

    return bad_urls


def main():
    """Run the whole process, in a function to keep namespace clean."""

    return_code = 0

    args = consume_args(sys.argv[1:])
    marks = json.load(args.backup_file)

    structure = parseMark(marks)

    all_urls = structure.collect_urls()
    print('Found {:,} bookmarks.'.format(len(all_urls)))

    urls_set = set(all_urls)
    print("found {:,} unique links.".format(len(urls_set)))

    if args.dead:
        bad_urls = verify_urls(urls_set, args.limit)

        if bad_urls:
            return_code = 1
            print("\nThe following URLs had errors:")
            for url in bad_urls:
                print("    {}: {}".format(url, bad_urls[url]))
        else:
            print("\nAll links were retrieved successfully.")

    if not args.noduplicates:
        duplicates = find_dupes(structure)
        for url in duplicates:
            print(url)
            for path in duplicates[url]:
                print('    ' + path)

        dupe_paths = find_duplicated_paths(structure)
        if dupe_paths:
            print('Identical children:')
            for key, other in dupe_paths:
                print('  "{}" and "{}"'.format(key, other))
        if duplicates or dupe_paths:
            return_code += 2

    if not args.dead and args.noduplicates:
        print("Nothing else to do! (Both dead link check and duplicates check disabled).")

    return return_code


if __name__ == '__main__':
    code = main()
    sys.exit(code)
