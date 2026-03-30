import { AnimatePresence, motion } from 'framer-motion';

interface CelebrationPulseProps {
  show: boolean;
}

/**
 * Green ring that expands and fades out.
 * Triggered on batch complete, QC pass, order shipped, etc.
 * Wire into status transitions in Phase 2.
 */
export function CelebrationPulse({ show }: CelebrationPulseProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="celebration-pulse"
          initial={{ opacity: 0.8, scale: 0.6 }}
          animate={{ opacity: 0, scale: 2.2 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"
        >
          <div className="h-12 w-12 rounded-full border-4 border-green-400" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface CelebrationCheckProps {
  show: boolean;
}

/**
 * Animated green checkmark that scales in then fades.
 */
export function CelebrationCheck({ show }: CelebrationCheckProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="celebration-check"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <motion.path
                d="M5 13l4 4L19 7"
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.35, delay: 0.1 }}
              />
            </svg>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
