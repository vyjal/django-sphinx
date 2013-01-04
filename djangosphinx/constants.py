#coding: utf-8

__author__ = 'ego'


# MySQL
QUERY_RANKERS = [
    'proximity_bm25',
    'bm25',
    'none',
    'wordcount',
    'proximity',
    'matchany',
    'fieldmask',
    'sph04',
    'expr',
]

QUERY_OPTIONS = dict(
    ranker=(str, unicode),
    max_matches=int,
    cutoff=int,
    max_query_time=int,
    retry_delay=int,
    field_weights=dict,
    index_weights=dict,
    reverse_scan=(int, bool),
    #comment=(str, unicode), # комменты пока оставлять нельзя.

)

# API

EMPTY_RESULT_SET = dict(
    total=0,
    total_found=0,
    words={},
    time=0.0,
)

# Both


SNIPPETS_OPTIONS = dict(                # DEFAULTS
    before_match=(str, unicode),        # '<b>'
    after_match=(str, unicode),         # '</b>'
    chunk_separator=(str, unicode),     # '...'
    limit=int,                          # 256
    around=int,                         # 5
    exact_phrase=bool,                  # False
    single_passage=bool,                # False
    use_boundaries=bool,                # False
    weight_order=bool,                  # False
    query_mode=bool,                    # False
    force_all_words=bool,               # False
    limit_passages=int,                 # 0
    limit_words=int,                    # 0
    start_passage_id=int,               # 1
    load_files=bool,                    # False
    load_files_scattered=bool,          # False
    html_strip_mode=(str, unicode),     # "none" ("none", "strip", "index", "retain")
    allow_empty=bool,                   # False
    passage_boundary=(str, unicode),    # N/A ("sentence", "paragraph", "zone")
    emit_zones=bool,                    # False
)

FILTER_CMP_OPERATIONS = dict(gt='>', lt='<', gte='>=', lte='<=')
FILTER_CMP_INVERSE = dict(gt='<=', lt='>=', gte='<', lte='>')
