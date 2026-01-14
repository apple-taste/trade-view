import { logger } from './logger';

/**
 * Performance monitoring utility
 * Used to track execution time of key operations
 */
class PerformanceMonitor {
  private marks: Map<string, number> = new Map();

  /**
   * Start measuring time for an operation
   * @param label Unique label for the operation
   */
  start(label: string) {
    this.marks.set(label, performance.now());
  }

  /**
   * End measuring time and log the duration
   * @param label Unique label for the operation
   * @param data Optional data to log with the duration
   */
  end(label: string, data?: any) {
    const startTime = this.marks.get(label);
    if (startTime === undefined) {
      logger.warn(`Performance warning: No start time found for label '${label}'`);
      return;
    }

    const duration = performance.now() - startTime;
    this.marks.delete(label);

    const message = `⏱️ [Performance] ${label}: ${duration.toFixed(2)}ms`;
    logger.info(message, data);

    return duration;
  }

  /**
   * Wrap an async function with performance monitoring
   * @param label Label for the operation
   * @param fn Async function to execute
   */
  async measureAsync<T>(label: string, fn: () => Promise<T>): Promise<T> {
    this.start(label);
    try {
      return await fn();
    } finally {
      this.end(label);
    }
  }

  /**
   * Wrap a synchronous function with performance monitoring
   * @param label Label for the operation
   * @param fn Function to execute
   */
  measure<T>(label: string, fn: () => T): T {
    this.start(label);
    try {
      return fn();
    } finally {
      this.end(label);
    }
  }
}

export const perfMonitor = new PerformanceMonitor();
