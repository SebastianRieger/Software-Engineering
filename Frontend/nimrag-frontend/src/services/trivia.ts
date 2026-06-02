import { getJson } from './api'
import type { TriviaQuestion } from '../types/trivia'

export function getTrivia(): Promise<TriviaQuestion> {
  return getJson<TriviaQuestion>('/trivia')
}
