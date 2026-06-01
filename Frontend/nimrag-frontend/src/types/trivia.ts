export interface TriviaQuestion {
  question: string
  correct_answer: string
  answers: string[]
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
  type: 'multiple' | 'boolean'
  source: 'live' | 'cache'
}
