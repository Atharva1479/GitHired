export type CategoryScore = {
  label: string;
  score: number;
  weight: number;
  description: string;
  fallback?: boolean;
};

export type KeywordPlacement = {
  section: string;
  type: "required" | "preferred" | "context";
};

export type SemanticMatch = {
  jd: string;
  resume: string;
  similarity: number;
};

export type WordSemanticMatch = {
  jd_term: string;
  resume_term: string;
  similarity: number;
};

export type SynonymMatch = {
  keyword: string;
  matched_alias: string;
};

export type AnalysisResult = {
  overall_score: number;
  grade: string;
  categories: {
    keyword_match: CategoryScore;
    required_coverage: CategoryScore;
    semantic_sentence: CategoryScore;
    word_semantic: CategoryScore;
    ontology_match: CategoryScore;
    experience: CategoryScore;
    education: CategoryScore;
    parsability: CategoryScore;
  };
  matched_keywords: string[];
  missing_keywords: string[];
  required_missing: string[];
  preferred_missing: string[];
  keyword_placement: Record<string, KeywordPlacement>;
  synonym_matches: SynonymMatch[];
  semantic_matches: SemanticMatch[];
  word_semantic_matches: WordSemanticMatch[];
  suggestions: string[];
  sections: {
    found: string[];
    missing: string[];
    ats_risks: string[];
  };
  experience_data: {
    total_years: number;
    weighted_years: number | null;
    required_years: number | null;
    degree_found: boolean;
  };
  occupation_context: {
    detected_title: string;
    implicit_skills_added: string[];
  };
  jd_structure: {
    required_count: number;
    preferred_count: number;
    context_count: number;
  };
  keyword_stats: {
    total_jd_keywords: number;
    matched_count: number;
    missing_count: number;
    required_missing_count: number;
    match_percentage: number;
  };
  ml_status: {
    semantic_sentence_active: boolean;
    word_semantic_active: boolean;
  };
};
