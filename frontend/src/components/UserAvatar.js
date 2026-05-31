import React, { useMemo } from 'react';
import './UserAvatar.css';

function UserAvatar({ name, fallback = 'U', size = 'md' }) {
  const initial = useMemo(() => {
    const source = (name || '').trim();
    return (source.charAt(0) || fallback).toUpperCase();
  }, [fallback, name]);

  return <div className={`user-avatar user-avatar-${size}`}>{initial}</div>;
}

export default UserAvatar;
