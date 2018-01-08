
# External imports
from lxml import html
import requests
import ujson


class _Note:
    
    __slots__ = ('notes_number', 'note_url', 'profile', 'page_id')
    
    def __init__(self, **kwargs):
        self.profile = kwargs['profile']
        
        note_url = kwargs.get('note_url')

        if note_url:
            return
        
        self.page_id = kwargs['page_id']
        self.notes_number = kwargs['notes_number']
        
    @staticmethod
    def _get_url(page_id, notes_number) -> str:
        return ''.join((
            'https://www.facebook.com/ajax/pagelet/generic.php/',
            'TimelineNotesPagelet?dpr=1&data={"s":',
            str(notes_number),
            ',"scroll_load":true,"profile_id":',
            str(page_id),
            ',"is_pages_tab":true,"tab_key":"notes"}&__user=0',
            '&__a=1&__req=d&__be=-1',
        ))
    
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
        res = requests.get(url)
        json_response = res.content.decode()[9:]
        _dict = ujson.loads(json_response)
        html_str = _dict['payload']
        return html.document_fromstring(html_str)

    def _extract_metadata_single_note(self, html_note):
        header = html_note.find_class('_39k2')[0]
        title = header.find_class('_4lmk _5s6c')[0].text
        links = header.findall('.//a')
        author = links[0].text
        url = 'https://facebook.com' + links[1].get('href')
        publication_date = links[1].text

        image = html_note.find_class('_5bdz')[0]
        background_image = image.get('style').split(';')[0]
        image_url = background_image.split('background-image: ')[1][4:-1]
        
        return {
            'author': author,
            'publication_date': publication_date,
            'title': title,
            'url': url,
            'image_url': image_url,
        }
    
    def _extract_content_single_note(self, html_note):
        body = html_note.find_class('_39k5 _5s6c')[0]
        content = []
        for child in body.getchildren():
            if child.tag == 'div':
                # It is a paragraph of text
                text = child.text_content()
                if text:
                    content.append({
                        'type': 'text',
                        'content': text,
                    })

            if child.tag == 'figure':
                # it is an embed image
                image = child.find('.//img')
                content.append({
                    'type': 'image',
                    'url': image.get('src')
                })
        
        return {
            'content': content,
        }

    def _extract_metadata(self, html_note) -> dict:
        html_note_header = html_note.find_class('_5x46')[0]

        time_tag = html_note_header.find_class('_5ptz')[0]
        publication_date = time_tag.get('title')
        publication_timestamp = time_tag.get('data-utime')
        
        embedded_note = html_note.find_class('mtm')[0]
        
        url = 'https://facebook.com' + embedded_note.find('.//a').get('href')

        author_link_tag = html_note_header.find_class('fwb')[0].find('.//a')
        author = author_link_tag.text

        return {
            'author': author,
            'publication_date': publication_date,
            'publication_timestamp': publication_timestamp,
            'url': url,
        }

    @staticmethod
    def get(profile: str, notes_number: int):
        page_id = _Note._get_page_id(profile)
        
        notes = _Note(
            profile=profile,
            page_id=page_id,
            notes_number=notes_number
        )
        
        notes_url = notes._get_url(page_id, notes_number)
        html_page = notes._fetch_data(notes_url)
        result = []

        for html_note in html_page.find_class('fbUserContent'):
            metadata = notes._extract_metadata(html_note)
            note_url = metadata['url']
            note = _Note.get_from_url(note_url)
            note['publication_date'] = metadata['publication_date']
            note['publication_timestamp'] = metadata['publication_timestamp']
            result.append(note)
    
        return result

    @staticmethod
    def get_from_url(url: str):
        """
        Extract a facebook note.

        Params:
            - url: the url of a facebook note.
        """
        profile = url.split('/')[4]
        note = _Note(
            profile=profile,
            note_url=url,
        )

        content = requests.get(url).content
        html_note = html.fromstring(content)

        metadata = note._extract_metadata_single_note(html_note)
        content = note._extract_content_single_note(html_note)
        
        result = {}
        result.update(metadata)
        result.update(content)
        return result
