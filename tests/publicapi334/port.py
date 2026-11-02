"""Explicit source compatibility edits for source Roslyn4.4 and Csc5.3.

Keep the original NS2 target, original feature guards, public metadata and WAE.
The renamed private comparer retains its original equality implementation. Nullable
edits express existing null checks and internally supplied diagnostic properties.
"""
import re

def port_source(name, text):
    reasons = []
    if 'SymbolEqualityComparer' in text:
        text = re.sub(r'\bSymbolEqualityComparer\b', 'Roslyn12SymbolEqualityComparer', text)
        reasons.append('Rename the original internal comparer to avoid colliding with the later public Roslyn type; retain its implementation.')
    if name == 'DeclarePublicApiAnalyzer.Impl.cs':
        assert text.count('== NullableAnnotation.None') == 4
        text = text.replace('== NullableAnnotation.None', '== global::Analyzer.Utilities.Lightup.NullableAnnotation.None')
        text = text.replace('IMethodSymbol accessor)', 'IMethodSymbol? accessor)')
        text = text.replace('ImmutableDictionary<string, string>', 'ImmutableDictionary<string, string?>')
        text = text.replace('attribute.AttributeClass.Equals(typeForwardedToAttribute)', 'typeForwardedToAttribute.Equals(attribute.AttributeClass)')
        text = text.replace('attribute.AttributeConstructor.Parameters.Length == 1', 'attribute.AttributeConstructor?.Parameters.Length == 1')
        text = text.replace('attribute.ApplicationSyntaxReference.GetSyntax(cancellationToken).GetLocation()', 'attribute.ApplicationSyntaxReference?.GetSyntax(cancellationToken).GetLocation() ?? Location.None')
        reasons.append('Qualify the original nullable light-up enum; describe nullable accessors and diagnostic property values; handle nullable metadata attribute syntax.')
    if name == 'DeclarePublicApiAnalyzer.cs':
        text = text.replace('SourceText text = additionalText.GetText(', 'SourceText? text = additionalText.GetText(')
        reasons.append('Describe an additional text result as nullable before its existing null check.')
    if name in ['DeclarePublicApiFix.cs', 'AnnotatePublicApiFix.cs']:
        # These properties are filled by the same analyzer before it emits each
        # supported diagnostic; no runtime null check is removed or suppressed.
        text = re.sub(r'(diagnostic.Properties\[DeclarePublicApiAnalyzer\.\w+\])(?!\s*==)', r'\1!', text)
        text = text.replace('additional.FilePath, isPublic', 'additional.FilePath ?? additional.Name, isPublic')
        text = text.replace('IGrouping<SyntaxTree, Diagnostic>', 'IGrouping<SyntaxTree?, Diagnostic>')
        text = text.replace('Document document = project.GetDocument(grouping.Key);', 'Document? document = grouping.Key is null ? null : project.GetDocument(grouping.Key);')
        text = text.replace('SyntaxNode root = await', 'SyntaxNode? root = await').replace('SemanticModel semanticModel = await', 'SemanticModel? semanticModel = await')
        text = text.replace('var project = newSolution.GetProject(pair.Key);', 'var project = newSolution.GetProject(pair.Key) ?? throw new global::System.InvalidOperationException("The fix project no longer exists.");')
        text = text.replace('protected override async Task<Solution> GetChangedSolutionAsync', 'protected override async Task<Solution?> GetChangedSolutionAsync')
        text = text.replace('protected override Task<Solution> GetChangedSolutionAsync', 'protected override async Task<Solution?> GetChangedSolutionAsync')
        text = text.replace('return _createChangedAdditionalDocument(cancellationToken);', 'return await _createChangedAdditionalDocument(cancellationToken).ConfigureAwait(false);')
        text = text.replace('GetDocumentDiagnosticsAsync(fixAllContext.Document)', 'GetDocumentDiagnosticsAsync(fixAllContext.Document ?? throw new global::System.InvalidOperationException("Document scope requires a document."))')
        text = text.replace('fixAllContext.Document.Name', 'fixAllContext.Document!.Name')
        reasons.append('Adapt nullable Roslyn4.4 property/document/tree contracts; retain nullable override contracts on private action classes.')
    if name == 'NullableEnablePublicApiFix.cs':
        text = text.replace('protected override async Task<Solution> GetChangedSolutionAsync', 'protected override async Task<Solution?> GetChangedSolutionAsync')
        reasons.append('Match the nullable solution return contract on the private code-action override.')
    if name == 'PublicApiFixHelpers.cs':
        text = text.replace('fixAllContext.CodeActionEquivalenceKey.Split(', '(fixAllContext.CodeActionEquivalenceKey ?? throw new global::System.InvalidOperationException("A fix-all action requires an equivalence key.")).Split(')
        reasons.append('Handle the later nullable equivalence-key contract.')
    if name == 'SyntaxGeneratorExtensions.cs':
        text = text.replace('compilation.GetOrCreateTypeByMetadataName(SystemNotImplementedExceptionTypeName))))', 'compilation.GetOrCreateTypeByMetadataName(SystemNotImplementedExceptionTypeName) ?? throw new global::System.InvalidOperationException("System.NotImplementedException is unavailable."))))')
        reasons.append('Require the exception type before creating its syntax node.')
    return text, reasons
