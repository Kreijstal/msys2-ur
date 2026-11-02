namespace GenFacadesFixture {
 public class Api<T> : System.IDisposable {
  public Api() { }
  public static T Echo(T value) { return value; }
  public int Value { get { return 1; } set { } }
  public event System.EventHandler Changed { add { } remove { } }
  public void Dispose() { }
 }
 public class Excluded { public void Removed() { } }
}
