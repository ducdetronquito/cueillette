from datetime import datetime
from typing import List, Optional

from ..utils import remove_class

from lxml import html
import requests
import ujson

# TODO
#   - Search a good caching system.
#   - Add method to extract post from a post url. (_Post.get_one())
#   - Extract videos from /videos

# Cli API:
#   - cueillette provider
#   - cueillette facebook posts --timestamp 1494945 --number 5
#   - cueillette facebook posts --date 2017-06-12 --time 08:00 --number 5


class _Post:
    __slots__ = (
        'date', 'number', 'page_id', 'profile', 'starting_timestamp'
    )

    def __init__(self, **kwargs):
        self.date = kwargs['date']
        self.number = kwargs['number']
        self.profile = kwargs['profile']
        self.starting_timestamp = kwargs['starting_timestamp']

    def _get_timeline_url(self) -> str:
        """
            Returns the timeline url of a profile page.
        """
        return ''.join((
            'https://www.facebook.com/pages_reaction_units/more/?page_id=',
            str(self.page_id),
            '&cursor={%22timeline_cursor%22:%22timeline_unit:1:0000000000',
            str(self.starting_timestamp),
            '%22,%22timeline_section_cursor%22:{}',
            ',%22has_next_page%22:true}&surface=www_pages_home&unit_count=',
            str(self.number),
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

        author_link_tag = html_post_header.find_class('fwb fcg')[0].find('a')
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

        # If the post contains a facebook video
        if media_tag.find('.//video') is not None:
            video_header = media_tag.find_class('_567_')[0]
            video_metadata = video_header.find_class('_2za_')[0]
            video_link = video_metadata.get('href')
            video_title = video_metadata.text_content()
            media = {
                'type': 'facebook video',
                'url': 'https://facebook.com' + video_link,
                'title': video_title,
            }
        else:
            media_link = media_tag.find('.//a')

            media_link_url = media_link.get('href')

            if ('/' + self.profile) in media_link_url:
                # The media is a facebook content
                media_link_url = media_link.get('href')
                if 'permalink' in media_link_url:
                    # The media is a shared facebook posts
                    # /!\ For now it seems that it is not possible to
                    #     grab this content type.
                    media = {
                        'type': 'facebook post',
                        'url': media_link_url,
                    }
                else:
                    # Otherwise the media is a facebook image.
                    image = media_link.find('.//img')
                    media = {
                        'type': 'facebook image',
                        'url': image.get('src'),
                    }
            else:
                # The media is a external hyperlink.
                # The link href contains a polluted facebook link.
                # However, we can still find the original link in
                # the *onmouseover* attribute.
                url = media_link.get('onmouseover').split('"')[1]
                url = url.replace('\\', '')
                media = {
                    'type': 'external hyperlink',
                    'url': url,
                }
                title = media_link.text_content()

                if title:
                    media['title'] = title

        return {
            'media': media
        }

    def _fetch_page_id(self) -> str:
        """
            Returns the page_id of a facebook profile.

            The page_id is extracted from the mobile profile frontpage
            because the page is much lighter than the desktop version.

            The page_id is hidden inside the profile picture link.
        """
        mobile_frontpage_url = 'https://m.facebook.com/{}'.format(self.profile)
        response = requests.get(mobile_frontpage_url)
        html_page = html.fromstring(response.content)
        header = html_page.get_element_by_id('m-timeline-cover-section')
        profile_pic_link = header.find('.//a').get('href')
        page_id = profile_pic_link.split('/')[3].split('.')[3]

        self.page_id = page_id

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

        posts = []
        for html_post in html_page.find_class('fbUserContent'):
            post = {}
            text = self._extract_text_content(html_post)
            post.update(text)
            metadata = self._extract_metadata(html_post)
            post.update(metadata)
            media = self._extract_multimedia_content(html_post)
            post.update(media)
            posts.append(post)
        return posts
    
    @staticmethod
    def get(profile: str, date: str, post_number: int) -> List[dict]:
        """
            Returns a list of facebook posts.
            
            Params:
                - profile: the name of a facebook profile.
                - date: a YYYY/MM/DD formated date.
                - post_number: the number of post to extract before
                               the *date* date.
        """
        starting_timestamp = datetime.strptime(date, '%Y-%m-%d').timestamp()
        starting_timestamp = int(starting_timestamp)
        
        posts = _Post(
            profile=profile,
            date=date,
            starting_timestamp=starting_timestamp,
            number=post_number,
        )
        posts._fetch_page_id()

        return posts._get()


# Alias internal bridge class to have a more readable API.
posts = _Post
