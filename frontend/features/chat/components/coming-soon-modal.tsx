import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ComingSoonModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  feature: string;
}

export function ComingSoonModal({ isOpen, onClose, title, feature }: ComingSoonModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-md flex flex-col overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-2xl"
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-800">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                {title}
                <Badge className="bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300">
                  Coming Soon
                </Badge>
              </h3>
              <button
                onClick={onClose}
                className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-full text-neutral-500 dark:text-neutral-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6">
              <p className="text-neutral-600 dark:text-neutral-400">
                {feature} is currently under development and will be available in a future update.
              </p>
              
              <div className="flex justify-end mt-6">
                <Button onClick={onClose} className="rounded-full">
                  Got it
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
