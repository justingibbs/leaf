import { useState, useEffect } from 'react'
import { Save, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

interface CardEditorProps {
  initialCode: string
  onSave?: (code: string) => void
  isSaving?: boolean
  readOnly?: boolean
}

export function CardEditor({ initialCode, onSave, isSaving, readOnly }: CardEditorProps) {
  const [code, setCode] = useState(initialCode)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setCode(initialCode)
    setHasChanges(false)
  }, [initialCode])

  const handleChange = (value: string) => {
    setCode(value)
    setHasChanges(value !== initialCode)
  }

  const handleSave = () => {
    if (onSave && hasChanges) {
      onSave(code)
      setHasChanges(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {!readOnly && (
        <div className="flex items-center justify-between p-2 border-b bg-muted/30">
          <span className="text-sm text-muted-foreground">
            {hasChanges ? 'Unsaved changes' : 'No changes'}
          </span>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save
          </Button>
        </div>
      )}
      <div className="flex-1 overflow-hidden">
        <Textarea
          value={code}
          onChange={(e) => handleChange(e.target.value)}
          readOnly={readOnly}
          className="h-full w-full font-mono text-sm resize-none rounded-none border-0 focus-visible:ring-0"
          placeholder="# Python code will appear here"
        />
      </div>
    </div>
  )
}
