'''
Config setup for Ameryn utils.
(C) 2015 Ameryn Media, LLC
'''

from ConfigParser import ConfigParser
import logging

CONFIG_LOCATION = 'ameryn.ini'

c = ConfigParser()
c.read(CONFIG_LOCATION)

log_level = logging.WARNING if c.get('general', 'log_level') == 'warning' else logging.INFO
pool_processing = c.getboolean('general', 'pool_processing')
drive_client_email = c.get('general', 'drive_client_email')
drive_private_key = c.get('general', 'drive_private_key').replace('\\n', '\n')
base_url = c.get('general', 'base_url')

input_orders = [order.strip().zfill(5) for order in c.get('input', 'input_orders').strip().split(',') if order.strip()]
input_items = [item.strip() for item in c.get('input', 'input_items').strip().split(',') if item.strip()]
input_whole_folder = False if input_orders or input_items else True
serial_series_start = c.getint('input', 'serial_series_start') if c.get('input', 'serial_series_start') else None
serial_series_end = c.getint('input', 'serial_series_end') if c.get('input', 'serial_series_end') else None
serial_series = range(serial_series_start, serial_series_end) if serial_series_start else None

boxes_path = c.get('paths', 'boxes_path')
cd_tracks_folder = c.get('paths', 'cd_tracks_folder')
clean_folder = c.get('paths', 'clean_folder')
csv_folder = c.get('paths', 'csv_folder')
db_path = c.get('paths', 'db_path')
digital_folder = c.get('paths', 'digital_folder')
discogs_folder = c.get('paths', 'discogs_folder')
dropbox_folder = c.get('paths', 'dropbox_folder')
font_path = c.get('paths', 'font_path')
images_folder = c.get('paths', 'images_folder')
log_folder = c.get('paths', 'log_folder')
order_notes_folder = c.get('paths', 'order_notes_folder')
pdf_folder = c.get('paths', 'pdf_folder')
ptburn_folder = c.get('paths', 'ptburn_folder')
raw_input_folders = c.get('paths', 'raw_input_folders')
raw_output_folder = c.get('paths', 'raw_output_folder')
recorded_archive_folder = c.get('paths', 'recorded_archive_folder')
resplit_list_path = c.get('paths', 'resplit_list_path')
resplit_track_lists_path = c.get('paths', 'resplit_track_lists_path')
resplit_artists_path = c.get('paths', 'resplit_artists_path')
server_clean_folder = c.get('paths', 'server_clean_folder')
server_split_folder = c.get('paths', 'server_split_folder')
split_folder = c.get('paths', 'split_folder')
thumbs_folder = c.get('paths', 'thumbs_folder')
tracked_folder = c.get('paths', 'tracked_folder')
watermark_path = c.get('paths', 'watermark_path')

track_silence_thresh = c.getint('track_customers', 'track_silence_thresh')
track_audio_min_length = c.getint('track_customers', 'track_audio_min_length')
track_silence_min_length = c.getint('track_customers', 'track_silence_min_length')
interside_silence_min_length = c.getint('track_customers', 'interside_silence_min_length')

input_resplit_list = c.getboolean('split', 'input_resplit_list')
split_export_format = c.get('split', 'split_export_format')

digital_formats = [digital_format.strip() for digital_format in c.get('print_labels', 'digital_formats').strip().split(',')]
layout_debug = c.getboolean('print_labels', 'layout_debug')
dropbox_move = c.getboolean('print_labels', 'dropbox_move')
just_add_tags = c.getboolean('print_labels', 'just_add_tags')
include_serial_in_digital_filename = c.getboolean('print_labels', 'include_serial_in_digital_filename')
cd_pdf_toggle = c.getboolean('print_labels', 'cd_pdf_toggle')
front_pdf_toggle = c.getboolean('print_labels', 'front_pdf_toggle')
back_pdf_toggle = c.getboolean('print_labels', 'back_pdf_toggle')
digital_files_toggle = c.getboolean('print_labels', 'digital_files_toggle')
burn_cds_toggle = c.getboolean('print_labels', 'burn_cds_toggle')
mp3_bitrate = c.get('print_labels', 'mp3_bitrate')

use_boxes_csv = c.getboolean('discogs', 'use_boxes_csv')
log_to_file = c.getboolean('discogs', 'log_to_file')
discogs_request_interval = c.getfloat('discogs', 'discogs_request_interval')
min_correlation = c.getfloat('discogs', 'min_correlation')
max_search_tries = c.getint('discogs', 'max_search_tries')
max_error_tries = c.getint('discogs', 'max_error_tries')

wc_ck = c.get('dbox', 'wc_ck')
wc_cs = c.get('dbox', 'wc_cs')
dbox_token = c.get('dbox', 'dbox_token')

overwrite_source = c.getboolean('strip', 'overwrite_source')
strip_suffix = c.getboolean('strip', 'strip_suffix')
strip_silence_thresh = c.getint('strip', 'strip_silence_thresh')
strip_silence_chunk = c.getint('strip', 'strip_silence_chunk')