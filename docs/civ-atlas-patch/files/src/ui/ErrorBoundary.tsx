import { Component, type ReactNode } from 'react';
import styles from './ErrorBoundary.module.css';

interface Props {
  children: ReactNode;
  title?: string;
  /** Remount only isolated, read-only views. Whole applications reload explicitly. */
  retry?: 'remount' | 'reload';
}

export class ErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() { return { failed: true }; }

  render() {
    if (!this.state.failed) return this.props.children;
    const remount = this.props.retry === 'remount';
    return <section className={styles.panel} role="alert" aria-label={this.props.title ?? '页面显示失败'}>
      <strong>{this.props.title ?? '页面显示失败'}</strong>
      <p>{remount ? '地图暂时无法绘制，请重试。' : '页面遇到错误，请重新加载。尚未保存的输入可能需要重新填写。'}</p>
      <button type="button" onClick={() => remount ? this.setState({ failed: false }) : window.location.reload()}>
        {remount ? '重新绘制地图' : '重新加载页面'}
      </button>
    </section>;
  }
}
