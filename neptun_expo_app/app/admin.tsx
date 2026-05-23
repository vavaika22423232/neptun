import { Redirect } from 'expo-router';

/** Flutter `/admin` — embed admin panel. */
export default function AdminRoute() {
  return <Redirect href="/web-embed?url=https%3A%2F%2Fneptun.in.ua%2Fadmin" />;
}
