import React from 'react';
import './LoadingSkeleton.css';

interface LoadingSkeletonProps {
    type?: 'text' | 'card' | 'table' | 'stat';
    count?: number;
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ type = 'text', count = 1 }) => {
    const renderSkeleton = () => {
        switch (type) {
            case 'card':
                return (
                    <div className="skeleton-card">
                        <div className="skeleton-line skeleton-title"></div>
                        <div className="skeleton-line skeleton-text"></div>
                        <div className="skeleton-line skeleton-text short"></div>
                    </div>
                );

            case 'table':
                return (
                    <div className="skeleton-table">
                        <div className="skeleton-table-header">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="skeleton-line"></div>
                            ))}
                        </div>
                        {[...Array(5)].map((_, rowIndex) => (
                            <div key={rowIndex} className="skeleton-table-row">
                                {[...Array(5)].map((_, colIndex) => (
                                    <div key={colIndex} className="skeleton-line"></div>
                                ))}
                            </div>
                        ))}
                    </div>
                );

            case 'stat':
                return (
                    <div className="skeleton-stat">
                        <div className="skeleton-circle"></div>
                        <div className="skeleton-stat-content">
                            <div className="skeleton-line skeleton-stat-value"></div>
                            <div className="skeleton-line skeleton-stat-label"></div>
                        </div>
                    </div>
                );

            case 'text':
            default:
                return <div className="skeleton-line"></div>;
        }
    };

    return (
        <>
            {[...Array(count)].map((_, index) => (
                <div key={index} className="skeleton-wrapper">
                    {renderSkeleton()}
                </div>
            ))}
        </>
    );
};

export default LoadingSkeleton;
