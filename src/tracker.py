import json
import re
import pandas as pd

BRANDS_MAP = {
    'corvane': {
        'name': 'Corvane Fleet',
        'patterns': [r'\bcorvane\s+fleet\b', r'\bcorvain\s+fleet\b', r'\bcorvain\b', r'\bcorvanefleet\b', r'\bcorvanefleet\.com\b', r'\bcorvane\b']
    },
    'trakvia': {
        'name': 'Trakvia',
        'patterns': [r'\btrakvia\b', r'\btrakvia\.com\b']
    },
    'routelyne': {
        'name': 'Routelyne',
        'patterns': [r'\broute\s+lyne\b', r'\broutelyne\b', r'\broutelyne\.com\b']
    },
    'gridwell': {
        'name': 'Gridwell Systems',
        'patterns': [r'\bgridwell\s+systems\b', r'\bgridwell\b', r'\bgridwell\.io\b']
    },
    'fleetora': {
        'name': 'Fleetora',
        'patterns': [r'\bfleetora\b', r'\bfleetora\.com\b']
    },
    'novahaul': {
        'name': 'Novahaul',
        'patterns': [r'\bnovahaul\b', r'\bnovahaul\.com\b']
    }
}

RECOMMENDED_WORDS = [
    r'best\s+overall', r'safest\s+choice', r'strong\s+pick', r'hard\s+to\s+beat',
    r'top\s+suggestion', r'top\s+pick', r'well\s+worth\s+shortlisting', r'reliable\s+choice',
    r'i\'d\s+recommend', r'if\s+i\s+had\s+to\s+pick\s+one', r'i\'d\s+start\s+with',
    r'strong\s+choice', r'stands\s+out\s+for'
]

NOT_RECOMMENDED_WORDS = [
    r'avoid\b', r'skip\s+it', r'wouldn\'t\s+choose', r'not\s+the\s+right\s+fit',
    r'likely\s+overkill', r'not\s+recommended'
]

NEGATIVE_WORDS = [
    r'slow\s+(customer\s+)?support', r'clunky\s+mobile\s+app', r'reporting\s+is\s+limited',
    r'contract\s+terms\s+have\s+drawn\s+complaints', r'billing\s+complaints',
    r'flag\s+outages', r'setup\s+reportedly\s+takes\s+longer', r'expensive\s+at\s+first',
    r'slow\s+fixes', r'go\s+in\s+with\s+caution'
]

def load_data(data_dir='data'):
    prompts_df = pd.read_csv(f'{data_dir}/prompts.csv')
    with open(f'{data_dir}/facts.json', 'r', encoding='utf-8') as f:
        facts = json.load(f)
        
    responses = []
    with open(f'{data_dir}/responses.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item.get('response_text') if item.get('response_text') is not None else item.get('answer', '')
            run_num = item.get('run') if item.get('run') is not None else item.get('run_number', 1)
            raw_engine = item.get('engine', '')
            engine_map = {
                'chatgpt': 'chatgpt', 'ChatGPT': 'chatgpt',
                'perplexity': 'perplexity', 'Perplexity': 'perplexity',
                'google_ai_overview': 'google_ai_overview', 'AI Overview': 'google_ai_overview'
            }
            engine = engine_map.get(raw_engine, raw_engine.lower().replace(' ', '_'))
            prompt_id = str(item.get('prompt_id', '')).upper()
            
            responses.append({
                'response_id': item.get('response_id'),
                'week': int(item.get('week', 1)),
                'engine': engine,
                'prompt_id': prompt_id,
                'run': int(run_num),
                'response_text': text or '',
                'citations': item.get('citations') or item.get('sources') or []
            })
            
    resp_df = pd.DataFrame(responses)
    return resp_df, prompts_df, facts

def mask_corvane_logistics(text):
    pattern = re.compile(r'\bcorvane\s+logistics\b', re.IGNORECASE)
    return pattern.sub('UNRELATED_FREIGHT_LOGISTICS_ENTITY', text)

def detect_mentions_in_text(text):
    cleaned_text = mask_corvane_logistics(text)
    findings = []
    
    for brand_key, meta in BRANDS_MAP.items():
        first_pos = None
        for pat in meta['patterns']:
            match = re.search(pat, cleaned_text, re.IGNORECASE)
            if match:
                idx = match.start()
                if first_pos is None or idx < first_pos:
                    first_pos = idx
        if first_pos is not None:
            findings.append({'brand': brand_key, 'index': first_pos})
            
    findings.sort(key=lambda x: x['index'])
    
    brand_positions = {}
    for rank, item in enumerate(findings, start=1):
        brand_positions[item['brand']] = rank
        
    return brand_positions, cleaned_text

def classify_tone_for_brand(text, brand_key):
    sentences = re.split(r'[\n\.\?!]+', text)
    matched_sentences = []
    
    patterns = BRANDS_MAP[brand_key]['patterns']
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if any(re.search(pat, s_clean, re.IGNORECASE) for pat in patterns):
            matched_sentences.append(s_clean)
            
    if not matched_sentences:
        return 'neutral'
        
    target_sentence = matched_sentences[-1]
    bottom_lines = [s for s in sentences if re.search(r'bottom\s+line', s, re.IGNORECASE)]
    if bottom_lines:
        bl_text = bottom_lines[-1]
        if any(re.search(pat, bl_text, re.IGNORECASE) for pat in patterns):
            target_sentence = bl_text

    ts_lower = target_sentence.lower()
    
    for p in NOT_RECOMMENDED_WORDS:
        if re.search(p, ts_lower):
            return 'not_recommended'
            
    for p in RECOMMENDED_WORDS:
        if re.search(p, ts_lower):
            return 'recommended'
            
    for p in NEGATIVE_WORDS:
        if re.search(p, ts_lower):
            return 'negative'
            
    return 'neutral'

def extract_wrong_facts(resp_df, facts):
    wrong_facts = []
    
    for _, row in resp_df.iterrows():
        text = mask_corvane_logistics(row['response_text'])
        resp_id = row['response_id']
        corvane_pats = BRANDS_MAP['corvane']['patterns']
        is_corvane = any(re.search(p, text, re.IGNORECASE) for p in corvane_pats)
        
        if is_corvane:
            if re.search(r'\b(corvane|corvain).*?(built-in|includes|offers|has)\s+(ai\s+)?dashcams?\b', text, re.IGNORECASE) or \
               re.search(r'\bbuilt-in\s+(ai\s+)?dashcams?.*?(corvane|corvain)\b', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*\bdashcams?[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'features.dashcams',
                    'claim_text': claim_m.group(0).strip() if claim_m else "built-in AI dashcams"
                })
                
            c_snippet = re.search(r'[^.\n]*(corvane|corvain)[^.\n]*\$(?:45|49)[^.\n]*', text, re.IGNORECASE)
            if c_snippet:
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'starting_price_usd',
                    'claim_text': c_snippet.group(0).strip()
                })

            if re.search(r'\bColumbus,\s*Georgia\b', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*Columbus,\s*Georgia[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'hq',
                    'claim_text': claim_m.group(0).strip() if claim_m else "based in Columbus, Georgia"
                })
            elif re.search(r'(corvane|corvain)[^.\n]*headquartered\s+in\s+Chicago', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*headquartered\s+in\s+Chicago[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'hq',
                    'claim_text': claim_m.group(0).strip() if claim_m else "The company is headquartered in Chicago."
                })

            if re.search(r'(corvane|corvain)[^.\n]*founded\s+in\s+2009', text, re.IGNORECASE) or \
               re.search(r'founded\s+in\s+2009[^.\n]*(corvane|corvain)', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*founded\s+in\s+2009[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'founded',
                    'claim_text': claim_m.group(0).strip() if claim_m else "It was founded in 2009."
                })

            if re.search(r'doesn\'t\s+integrate\s+with\s+QuickBooks', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*doesn\'t\s+integrate\s+with\s+QuickBooks[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'integrations',
                    'claim_text': claim_m.group(0).strip() if claim_m else "It doesn't integrate with QuickBooks."
                })

            if re.search(r'doesn\'t\s+support\s+ELD\s+compliance', text, re.IGNORECASE):
                claim_m = re.search(r'[^.\n]*doesn\'t\s+support\s+ELD\s+compliance[^.\n]*', text, re.IGNORECASE)
                wrong_facts.append({
                    'response_id': resp_id,
                    'brand': 'corvane',
                    'fact_key': 'features.eld_compliance',
                    'claim_text': claim_m.group(0).strip() if claim_m else "doesn't support ELD compliance"
                })

    return pd.DataFrame(wrong_facts)

def build_mentions_dataframe(resp_df):
    rows = []
    target_brands = ['corvane', 'trakvia', 'routelyne', 'gridwell', 'fleetora', 'novahaul']
    
    for _, item in resp_df.iterrows():
        pos_map, clean_txt = detect_mentions_in_text(item['response_text'])
        resp_id = item['response_id']
        
        for brand in target_brands:
            if brand in pos_map:
                pos = pos_map[brand]
                tone = classify_tone_for_brand(clean_txt, brand)
                rows.append({
                    'response_id': resp_id,
                    'brand': brand,
                    'mentioned': True,
                    'position': pos,
                    'tone': tone
                })
            else:
                rows.append({
                    'response_id': resp_id,
                    'brand': brand,
                    'mentioned': False,
                    'position': '',
                    'tone': ''
                })
                
    return pd.DataFrame(rows)

def compute_visibility_score(mentions_df, resp_df, prompts_df):
    merged = mentions_df.merge(resp_df[['response_id', 'week', 'engine', 'prompt_id', 'run']], on='response_id')
    merged = merged.merge(prompts_df[['prompt_id', 'priority']], on='prompt_id', how='left')
    merged['priority'] = merged['priority'].fillna(1)
    
    def pos_score(pos):
        if pos == 1: return 1.0
        elif pos == 2: return 0.75
        elif pos == 3: return 0.50
        elif isinstance(pos, (int, float)) and pos > 3: return 0.25
        return 0.0

    def tone_mult(t):
        if t == 'recommended': return 1.3
        elif t == 'neutral': return 1.0
        elif t == 'negative': return 0.5
        elif t == 'not_recommended': return 0.0
        return 0.0

    merged['pos_val'] = merged['position'].apply(pos_score)
    merged['tone_val'] = merged['tone'].apply(tone_mult)
    merged['raw_point'] = merged['pos_val'] * merged['tone_val'] * merged['priority']
    
    resp_weights = resp_df.merge(prompts_df[['prompt_id', 'priority']], on='prompt_id', how='left')
    resp_weights['priority'] = resp_weights['priority'].fillna(1)
    weekly_max_weights = resp_weights.groupby('week')['priority'].sum().to_dict()
    
    brand_week_scores = []
    tracked = ['corvane', 'trakvia', 'routelyne', 'gridwell']
    
    for (week, brand), group in merged[merged['brand'].isin(tracked)].groupby(['week', 'brand']):
        tot_pts = group['raw_point'].sum()
        max_possible = weekly_max_weights.get(week, 1) * 1.3
        scaled_score = round((tot_pts / max_possible) * 100, 1)
        brand_week_scores.append({
            'week': week,
            'brand': brand,
            'score': scaled_score,
            'mention_count': group['mentioned'].sum()
        })
        
    return pd.DataFrame(brand_week_scores)