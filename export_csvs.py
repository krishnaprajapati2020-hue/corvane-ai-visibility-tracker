from src.tracker import load_data, build_mentions_dataframe, extract_wrong_facts

def main():
    print("Loading data...")
    resp_df, prompts_df, facts = load_data('data')
    
    print("Generating mentions.csv...")
    mentions_df = build_mentions_dataframe(resp_df)
    mentions_df.to_csv('mentions.csv', index=False)
    print(f"mentions.csv created successfully! ({len(mentions_df)} rows)")
    
    print("Generating wrong_facts.csv...")
    wrong_facts_df = extract_wrong_facts(resp_df, facts)
    wrong_facts_df.to_csv('wrong_facts.csv', index=False)
    print(f"wrong_facts.csv created successfully! ({len(wrong_facts_df)} contradictions found)")

if __name__ == '__main__':
    main()