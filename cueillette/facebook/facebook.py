from datetime import datetime
import re
from typing import List, Optional

from ..utils import remove_class

from lxml import html
import requests
import ujson

# TODO
#   - Search a good caching system.
#   - Extract videos from /videos

# Cli API:
#   - cueillette provider
#   - cueillette facebook posts --profile bhuphusis --timestamp 1494945 --number 5
#   - cueillette facebook posts --profile bhuphusis --date 2017-06-12 --time 08:00 --number 5
#   - cueillette facebook posts --url https://www.facebook.com/Cerclecritiquemarxien/posts/1785684571448466


class _Post:
    __slots__ = (
        'from_timestamp', 'page_id', 'post_number',
        'post_url', 'profile',
    )

    def __init__(self, **kwargs):
        self.post_url = kwargs.get('post_url')
        self.profile = kwargs['profile']

        if self.post_url:
            return

        self.from_timestamp = kwargs['from_timestamp']
        self.post_number = kwargs['post_number']
        self.page_id = kwargs['page_id']

    @staticmethod
    def _get_timeline_url(
            page_id: int,
            from_timestamp: int,
            post_number: int
        ) -> str:
        """
            Returns the timeline url of a profile page.
        """
        return ''.join((
            'https://www.facebook.com/pages_reaction_units/more/?page_id=',
            str(page_id),
            '&cursor={%22timeline_cursor%22:%22timeline_unit:1:0000000000',
            str(from_timestamp),
            '%22,%22timeline_section_cursor%22:{}',
            ',%22has_next_page%22:true}&surface=www_pages_home&unit_count=',
            str(post_number),
            '&__a=1'
        ))

    def _extract_text_content(self, html_post) -> dict:
        """
            Extract the text of a post.

            Params:
                - html_post: the tree of an html post.
        """
        html_text = html_post.find_class('userContent')[0]

        # Remove ellipses displayed when a post is too long.
        remove_class(html_text, 'text_exposed_hide')

        # Remove link displayed when a post is too long.
        remove_class(html_text, 'see_more_link_inner')

        return {
            'text_content': html_text.text_content()
        }

    def _extract_metadata(self, html_post) -> dict:
        """
            Extract metadata of a post.

            It extracts the following information:
                - author
                - publication_date
                - publication_timestamp
                - url

            Params:
                - html_post: the tree of an html post.
        """
        html_post_header = html_post.find_class('_5x46')[0]

        time_tag = html_post_header.find_class('_5ptz')[0]
        post_date = time_tag.get('title')
        post_timestamp = time_tag.get('data-utime')

        post_url = 'https://facebook.com' + time_tag.getparent().get('href')

        author_link_tag = html_post_header.find_class('fwb')[0].find('.//a')
        post_author = author_link_tag.text
        return {
            'author': post_author,
            'publication_date': post_date,
            'publication_timestamp': post_timestamp,
            'url': post_url,
        }

    def _extract_multimedia_content(self, html_post) -> Optional[dict]:
        """"
            Extract the multimedia content of a facebook post if it exists.

            Params:
                - html_post: the tree of an html post.
        """
        # Data regarding the media embedded in the post
        # can be found in the only div with the *mtm* class.
        media_tag = html_post.find_class('mtm')
        if not media_tag:
            return {}

        media_tag = media_tag[0]
        # The post contains a facebook video.
        if media_tag.find('.//video') is not None:
            video_header = media_tag.find_class('_567_')[0]
            video_metadata = video_header.find_class('_2za_')[0]
            video_link = video_metadata.get('href')
            video_title = video_metadata.text_content()
            return {
                'media': {
                    'type': 'facebook video',
                    'url': 'https://facebook.com' + video_link,
                    'title': video_title,
                }
            }

        media_link = media_tag.find('.//a')
        media_link_url = media_link.get('href')
        fb_photos_pattern = '^\\/.+\\/photos\\/'
        # The post contains a facebook photo.
        if re.search(fb_photos_pattern, media_link_url):
            image = media_link.find('.//img')

            if self.profile in media_link_url:
                media_type = 'facebook image'
            else:
                media_type = 'shared facebook image'

            return {
                'media': {
                    'type': media_type,
                    'url': image.get('src'),
                }
            }

        fb_shared_post_pattern = '^\/permalink.php?'
        # The post contains a shared facebook post.
        if re.search(fb_shared_post_pattern, media_link_url):
            return {
                'media': {
                    'type': 'shared facebook post',
                    'url': 'https://facebook.com' + media_link_url,
                }
            }

        # From here, the media muste be an external hyperlink.
        # The link href contains a polluted facebook link.
        # However, we can still find the original link in
        # the *onmouseover* attribute.
        external_url = media_link.get('onmouseover').split('"')[1]
        external_url = external_url.replace('\\', '')

        if 'https://www.youtube.com' in external_url:
            media_type = 'youtube video'
        else:
            media_type = 'external link'

        return {
            'media': {
                'type': media_type,
                'url': external_url,
            }
        }

    @staticmethod
    def _get_page_id(profile: str) -> str:
        """
            Returns the page_id of a facebook profile.

            The page_id is extracted from the mobile profile frontpage
            because the page is much lighter than the desktop version.

            The page_id is hidden inside the profile picture link.
        """
        mobile_frontpage_url = 'https://m.facebook.com/{}'.format(profile)
        response = requests.get(mobile_frontpage_url)
        html_page = html.fromstring(response.content)
        header = html_page.get_element_by_id('m-timeline-cover-section')
        profile_pic_link = header.find('.//a').get('href')
        page_id = profile_pic_link.split('/')[3].split('.')[3]
        return page_id

    def _fetch_data(self, url: str):
        """
            Returns the HTML tree of a facebook posts' timeline.

            The HTML content of a posts' timeline is hidden in a
            fat JSON blob.
        """
        res = requests.get(url)
        json_response = res.content.decode()[9:]
        _dict = ujson.loads(json_response)
        html_str = _dict['domops'][0][3]['__html']
        return html.document_fromstring(html_str)

    def _get(self) -> List[dict]:
        url = self._get_timeline_url()
        html_page = self._fetch_data(url)

        return [
            self._extract_post_content(html_post)
            for html_post in html_page.find_class('fbUserContent')
        ]

    def _extract_post_content(self, html_post) -> dict:
        post = {}
        text = self._extract_text_content(html_post)
        post.update(text)
        metadata = self._extract_metadata(html_post)
        post.update(metadata)
        media = self._extract_multimedia_content(html_post)
        post.update(media)
        return post

    @staticmethod
    def get_from_timeline(profile: str, **kwargs) -> List[dict]:
        """
            Returns a list of facebook posts.

            Params:
                - profile: the name of a facebook profile.

            Options:
                - from_date: a YYYY/MM/DD formated date.
                - from_timestamp: an epoch timestamp.
                - page_id: a facebook page id.
                - post_number: the number of post to extract before
                               the *date* date. (default is 8)
        """
        if 'from_date' not in kwargs and 'from_timestamp' not in kwargs:
            raise Exception(
                'You need to provide a date or a timestamp '
                'to be be able to extract facebook posts from '
                'a timeline.'
            )

        try:
            from_timestamp = kwargs['from_timestamp']
        except KeyError:
            from_timestamp = int(
                datetime.strptime(kwargs['from_date'], '%Y-%m-%d').timestamp()
            )

        post_number = kwargs.get('post_number', 8)
        page_id = kwargs.get('page_id') or _Post._get_page_id(profile)
        posts = _Post(
            profile=profile,
            from_timestamp=from_timestamp,
            post_number=post_number,
            page_id=page_id,
        )

        url = _Post._get_timeline_url(page_id, from_timestamp, post_number)
        res = requests.get(url)
        json_response = res.content.decode()[9:]
        _dict = ujson.loads(json_response)
        html_str = _dict['domops'][0][3]['__html']
        html_page = html.document_fromstring(html_str)

        return [
            posts._extract_post_content(html_post)
            for html_post in html_page.find_class('fbUserContent')
        ]

    @staticmethod
    def get_from_url(post_url: str) -> dict:
        """
            Extract a facebook post.

            Params:
                - post_url: the url of a facebook post.
        """
        # Extract profile name from url.
        profile = post_url.split('/')[3]
        post = _Post(
            profile=profile,
            post_url=post_url,
        )

        # Extract post tree from html page.
        content = requests.get(post_url).content
        html_page = html.fromstring(content)
        comment = html_page.find('.//code').getchildren()[0]
        html_page = html.document_fromstring(comment.text)
        html_post = html_page.find_class('fbUserContent')[0]

        return post._extract_post_content(html_post)


class _Note:

    def _get_timeline_url(self, number) -> str:
        return ''.join((
            'https://www.facebook.com/ajax/pagelet/generic.php/',
            'TimelineNotesPagelet?dpr=1&data={"s":',
            number,
            ',"scroll_load":true,"profile_id":1369416176408643,',
            '"is_pages_tab":true,"tab_key":"notes"}&__user=0',
            '&__a=1&__req=d&__be=-1',
        ))


# Alias internal bridge class to have a more readable API.
posts = _Post
notes = _Note
