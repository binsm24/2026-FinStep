import { useContext } from 'react'
import { ArrowRight, BookmarkCheck } from 'lucide-react'
import { ArchiveNavigation } from './navigation-context'

export default function ResultArchiveStatus({ savedResultId }: { savedResultId?: string }) {
  const openArchive = useContext(ArchiveNavigation)
  if (!savedResultId) return null
  return <section className="save-result-card result-archive-status" aria-label="결과 자동 저장">
    <h2><BookmarkCheck size={22} /> 보관함에 자동으로 저장했어요</h2>
    <p role="status">로그인한 상태에서 완료한 결과예요. 보관함에서 점수와 대화 기록을 다시 볼 수 있어요.</p>
    <button type="button" className="secondary-button" onClick={openArchive}>내 보관함으로 이동 <ArrowRight size={16} /></button>
  </section>
}
