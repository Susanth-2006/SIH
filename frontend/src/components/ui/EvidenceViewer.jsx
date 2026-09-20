import { useState } from 'react'
import { Image as ImageIcon, Video, FileQuestion, AlertCircle } from 'lucide-react'
import { resolveMedia } from '../../services/api'

export default function EvidenceViewer({ image, video, title }) {
  const [imageError, setImageError] = useState(false)
  const hasImage = !!image
  const hasVideo = !!video

  if (!hasImage && !hasVideo) {
    return (
      <div className="evidence-viewer">
        <div className="evidence-placeholder">
          <FileQuestion size={32} style={{ marginRight: 10 }} />
          No evidence available
        </div>
      </div>
    )
  }

  return (
    <div className="evidence-viewer">
      {hasImage &&
        (imageError ? (
          <div className="evidence-placeholder">
            <AlertCircle size={32} style={{ marginRight: 10 }} />
            Evidence could not be loaded
          </div>
        ) : (
          <img
            src={resolveMedia(image)}
            alt={title || 'Evidence'}
            onError={() => setImageError(true)}
          />
        ))}
      {hasVideo && <video src={resolveMedia(video)} controls />}
    </div>
  )
}

export function EvidenceThumbnail({ src, type, onClick }) {
  const [error, setError] = useState(false)
  return (
    <button
      onClick={onClick}
      style={{
        width: 72,
        height: 72,
        borderRadius: 8,
        overflow: 'hidden',
        border: '1px solid #e2e8f0',
        background: '#0f172a',
        cursor: 'pointer',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {type === 'VIDEO' ? (
        <Video size={20} color="white" />
      ) : src && !error ? (
        <img src={resolveMedia(src)} alt="evidence" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={() => setError(true)} />
      ) : (
        <ImageIcon size={20} color="white" />
      )}
    </button>
  )
}